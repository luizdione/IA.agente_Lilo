"""
chat/retriever.py — Recuperação densa simples sobre o BrainStore.
(Espaço para busca híbrida BM25 + densa numa próxima iteração.)
"""
from __future__ import annotations


class Retriever:
    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def search(self, query: str, n: int = 8, where: dict | None = None):
        q = self.embedder.embed_query(query)
        res = self.store.query(q, n_results=n, where=where)
        return res["documents"][0], res["metadatas"][0]
