"""
chat/rag_chain.py — Pipeline RAG: query -> retrieval -> contexto -> Lilo 3.0 -> resposta.

O gerador (Ollama) é injetável via ollama_fn para testes. A saída inclui chunks/metas
para alimentar o gate de verificação (ver verify.bridge.evidence_from_rag).
"""
from __future__ import annotations
from .prompts import build_prompt
from ..config import LLM_URL as OLLAMA_URL, LLM_MODEL as DEFAULT_MODEL


class ScholarRAG:
    def __init__(self, store, embedder, ollama_fn=None,
                 model: str = DEFAULT_MODEL, url: str = OLLAMA_URL):
        self.store = store
        self.embedder = embedder
        self.model = model
        self.url = url
        self._ollama_fn = ollama_fn        # injetável p/ testes

    def ask(self, question: str, n_chunks: int = 8, year_filter: int | None = None) -> dict:
        q_emb = self.embedder.embed_query(question)
        where = {"year": str(year_filter)} if year_filter else None
        results = self.store.query(q_emb, n_results=n_chunks, where=where)
        chunks = results["documents"][0]
        metas = results["metadatas"][0]
        if not chunks:
            return {"answer": "Nenhum paper relevante encontrado na biblioteca.",
                    "refs": [], "chunks": [], "metas": []}
        answer = self._generate(build_prompt(question, chunks, metas))
        refs = [
            f"[{i+1}] {(m.get('authors','').split(';')[0] or '?')} et al. "
            f"({m.get('year','')}) — {m.get('title','')[:80]}"
            for i, m in enumerate(metas)
        ]
        return {"answer": answer, "refs": refs, "chunks": chunks, "metas": metas}

    def _generate(self, prompt: str) -> str:
        if self._ollama_fn is not None:
            return self._ollama_fn(prompt)
        import httpx  # lazy
        r = httpx.post(self.url, json={
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2},   # baixo para respostas factuais
        }, timeout=120)
        return r.json().get("response", "")
