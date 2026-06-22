"""
brain/vector_store.py — Interface ChromaDB local persistente (import lazy).
Distância cosseno; metadados do paper por chunk.
"""
from __future__ import annotations
from ..config import BRAIN_DIR


class BrainStore:
    def __init__(self, persist_dir: str = BRAIN_DIR, collection: str = "papers"):
        import chromadb  # lazy
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"})

    def add_chunks(self, chunks, embeddings, paper_metadata: dict):
        self.collection.add(
            ids=[f"{c.paper_md5}_{c.chunk_index}" for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[{
                "paper_md5": c.paper_md5,
                "chunk_index": c.chunk_index,
                "section": c.section,
                "title": paper_metadata.get("title", ""),
                "authors": "; ".join(paper_metadata.get("authors", [])),
                "year": str(paper_metadata.get("year", "")),
                "journal": paper_metadata.get("journal", ""),
                "doi": paper_metadata.get("doi", ""),
                # antes ignorados: tema (classificação) e caminho do PDF
                "themes": "; ".join(paper_metadata.get("themes", []) or []),
                "path": paper_metadata.get("path", ""),
            } for c in chunks],
        )

    def query(self, query_embedding, n_results: int = 8, where: dict | None = None) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results, where=where,
            include=["documents", "metadatas", "distances"])

    def count(self) -> int:
        return self.collection.count()
