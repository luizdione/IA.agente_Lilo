"""
brain/embedder.py — Embeddings locais (sentence-transformers, import lazy).
Modelo: BAAI/bge-m3 (multilíngue PT/EN). Alternativa leve: all-MiniLM-L6-v2.
"""
from __future__ import annotations
from ..config import EMBED_MODEL as DEFAULT_MODEL


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        from sentence_transformers import SentenceTransformer  # lazy
        self.model = SentenceTransformer(model_name)

    def embed_chunks(self, chunks) -> list[list[float]]:
        return self.model.encode([c.text for c in chunks], show_progress_bar=True).tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.model.encode([query])[0].tolist()
