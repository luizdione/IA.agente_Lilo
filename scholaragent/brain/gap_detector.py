"""
brain/gap_detector.py -- Identifica lacunas na literatura para um tema.

Recupera os papers mais próximos do tema e pede ao LLM uma síntese de gaps
(contradições, populações não cobertas, métodos ausentes, perguntas em aberto).
O LLM entra por injeção (llm_fn) -> testável sem Ollama.
"""
from __future__ import annotations

from ..chat.prompts import gap_detection_prompt


class GapDetector:
    def __init__(self, store, embedder, llm_fn):
        self.store = store
        self.embedder = embedder
        self.llm_fn = llm_fn          # callable(prompt) -> str (injetável)

    def detect(self, theme: str, n_chunks: int = 12) -> dict:
        q = self.embedder.embed_query(theme)
        res = self.store.query(q, n_results=n_chunks)
        chunks = res["documents"][0]
        metas = res["metadatas"][0]
        if not chunks:
            return {"gaps": "Nenhum paper relevante encontrado na biblioteca.", "refs": []}
        summary = "\n\n".join(
            f"[{i+1}] {m.get('authors', '').split(';')[0]} ({m.get('year', '')}): {c[:300]}"
            for i, (c, m) in enumerate(zip(chunks, metas))
        )
        gaps = self.llm_fn(gap_detection_prompt(theme, summary))
        refs = [
            f"[{i+1}] {(m.get('title') or m.get('paper_md5', ''))[:80]} ({m.get('year', '')})"
            for i, m in enumerate(metas)
        ]
        return {"gaps": gaps, "refs": refs}
