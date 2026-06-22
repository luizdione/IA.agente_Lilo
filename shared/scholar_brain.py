"""
shared/scholar_brain.py -- Ponte do LILO para o ScholarAgent (RAG local + gate factual).

O pacote `scholaragent` vive na RAIZ do Lilo (import direto, sem caminho externo).
Fonte = biblioteca LOCAL de PDFs já ingerida (ChromaDB em data/scholar_brain), distinta
do agente 'scholar' do Lilo (busca ONLINE em PubMed/arXiv). Tudo local; LLM via Ollama :11434.
"""
from __future__ import annotations
from functools import lru_cache


def is_available() -> tuple[bool, str]:
    try:
        import scholaragent              # noqa: F401  (pacote top-level na raiz do Lilo)
        import chromadb                  # noqa: F401
        import sentence_transformers     # noqa: F401
    except Exception as e:
        return False, f"deps do scholaragent indisponíveis: {e}"
    return True, "ok"


@lru_cache(maxsize=1)
def _components():
    from scholaragent.brain.embedder import Embedder
    from scholaragent.brain.vector_store import BrainStore
    from scholaragent.chat.rag_chain import ScholarRAG
    from scholaragent.verify import build_grounder, VerificationGate, evidence_from_rag
    store = BrainStore()
    embedder = Embedder()
    rag = ScholarRAG(store, embedder)
    gate = VerificationGate(build_grounder(store, embedder, use_reranker=True))
    return store, rag, gate, evidence_from_rag


def library_count() -> int:
    try:
        store, *_ = _components()
        return store.count()
    except Exception:
        return 0


def ask(question: str, verify: bool = True, n_chunks: int = 8) -> dict:
    """Pergunta à biblioteca local. Retorna {answer, refs, decision, n_used}."""
    ok, msg = is_available()
    if not ok:
        return {"answer": f"[ScholarAgent] {msg}", "refs": [], "decision": None, "n_used": 0}
    try:
        store, rag, gate, evidence_from_rag = _components()
        if store.count() == 0:
            return {"answer": "[ScholarAgent] Biblioteca vazia — rode a ingestão.",
                    "refs": [], "decision": None, "n_used": 0}
        res = rag.ask(question, n_chunks=n_chunks)
        decision = None
        if verify and res["chunks"]:
            used, ref_map = evidence_from_rag(res["chunks"], res["metas"])
            decision = gate.verify("lilo", question, res["answer"], used, ref_map,
                                   write_trail=False).decision.value
        return {"answer": res["answer"], "refs": res["refs"],
                "decision": decision, "n_used": len(res["chunks"])}
    except Exception as e:
        return {"answer": f"[ScholarAgent] erro: {e}", "refs": [], "decision": None, "n_used": 0}
