"""
shared/scholar_brain.py -- Ponte para o ScholarAgent (RAG local + gate factual).

O ScholarAgent e um projeto externo (cerebro cientifico local: RAG sobre a
biblioteca de PDFs ja ingerida + gate de verificacao factual). Aqui o importamos
por caminho (SCHOLARAGENT_HOME) e expomos uma API minima para o LILO.

DISTINTO do agente 'scholar' do LILO (busca ONLINE em PubMed/arXiv): aqui a fonte
e a BIBLIOTECA LOCAL ja indexada (ChromaDB + embeddings locais), e a resposta
passa pelo gate (PASS/REVIEW/BLOCK). Tudo local; o LLM e o Ollama do LILO (:11434).
"""
from __future__ import annotations
import os
import sys
from functools import lru_cache

_DEFAULT_HOME = r"C:\Users\luizd\OneDrive\Data_Science\Projetos\scholaragent"
SCHOLAR_HOME = os.environ.get("SCHOLARAGENT_HOME", _DEFAULT_HOME)


def _ensure_path() -> None:
    if os.path.isdir(SCHOLAR_HOME) and SCHOLAR_HOME not in sys.path:
        sys.path.insert(0, SCHOLAR_HOME)
    # A base vetorial multilingue fica em <SCHOLAR_HOME>/brain_data_ml; fixa em caminho
    # ABSOLUTO para nao depender do CWD do LILO. setdefault respeita override explicito.
    os.environ.setdefault("SCHOLAR_BRAIN_DIR", os.path.join(SCHOLAR_HOME, "brain_data_ml"))


def is_available() -> tuple[bool, str]:
    """Verifica se o pacote scholaragent e suas deps estao acessiveis."""
    _ensure_path()
    if not os.path.isdir(SCHOLAR_HOME):
        return False, f"ScholarAgent nao encontrado em {SCHOLAR_HOME} (defina SCHOLARAGENT_HOME)."
    try:
        import scholaragent  # noqa: F401
        import chromadb       # noqa: F401
        import sentence_transformers  # noqa: F401
    except Exception as e:
        return False, f"deps do scholaragent indisponiveis: {e}"
    return True, "ok"


@lru_cache(maxsize=1)
def _components():
    """Carrega RAG + gate uma vez (lazy). store.count() consulta o DB ao vivo."""
    _ensure_path()
    from scholaragent.brain.embedder import Embedder
    from scholaragent.brain.vector_store import BrainStore
    from scholaragent.chat.rag_chain import ScholarRAG
    from scholaragent.verify import build_grounder, VerificationGate, evidence_from_rag
    store = BrainStore()
    embedder = Embedder()
    rag = ScholarRAG(store, embedder)
    # reranker ligado (cross-encoder multilingue leve) -> evidencia melhor p/ o gate;
    # se o modelo nao carregar, build_grounder cai p/ triagem por tokens.
    gate = VerificationGate(build_grounder(store, embedder, use_reranker=True))
    return store, rag, gate, evidence_from_rag


def library_count() -> int:
    """Numero de chunks indexados na biblioteca (0 se indisponivel/vazia)."""
    try:
        store, *_ = _components()
        return store.count()
    except Exception:
        return 0


def ask(question: str, verify: bool = True, n_chunks: int = 8) -> dict:
    """Pergunta a biblioteca local. Retorna {answer, refs, decision, n_used}."""
    ok, msg = is_available()
    if not ok:
        return {"answer": f"[ScholarAgent] {msg}", "refs": [], "decision": None, "n_used": 0}
    try:
        store, rag, gate, evidence_from_rag = _components()
        if store.count() == 0:
            return {"answer": "[ScholarAgent] Biblioteca vazia -- rode a ingestao "
                              "(scripts/ingest.py).",
                    "refs": [], "decision": None, "n_used": 0}
        res = rag.ask(question, n_chunks=n_chunks)
        decision = None
        if verify and res["chunks"]:
            used, ref_map = evidence_from_rag(res["chunks"], res["metas"])
            report = gate.verify("lilo-bridge", question, res["answer"], used, ref_map,
                                 write_trail=False)
            decision = report.decision.value
        return {"answer": res["answer"], "refs": res["refs"],
                "decision": decision, "n_used": len(res["chunks"])}
    except Exception as e:
        return {"answer": f"[ScholarAgent] erro: {e}", "refs": [], "decision": None, "n_used": 0}
