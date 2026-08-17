"""
brain/embedder.py — Embeddings locais do RAG (e do roteador do dashboard).

Default: **bge-m3 via Ollama** (GPU, multilíngue PT/EN, 1024-dim) — ver
`config.EMBED_MODEL`. NÃO exige torch+CUDA no Python: o Ollama já roda o modelo
na RTX 3060. Fallback automático: sentence-transformers (all-MiniLM /
paraphrase-multilingual) em CPU, caso o Ollama/bge-m3 não esteja disponível.

Para forçar sentence-transformers, aponte SCHOLAR_EMBED_MODEL para um modelo HF
(ex.: `paraphrase-multilingual-MiniLM-L12-v2`). Para outro modelo Ollama, use o
próprio nome (ex.: `bge-m3`, `mxbai-embed-large`) ou o prefixo `ollama:<modelo>`.
"""
from __future__ import annotations
import os
from ..config import EMBED_MODEL as DEFAULT_MODEL

# Modelos de embedding servidos pelo Ollama (GPU, sem torch+CUDA no Python).
_OLLAMA_EMBED = {
    "bge-m3", "bge-m3:latest",
    "mxbai-embed-large", "mxbai-embed-large:latest",
    "nomic-embed-text", "nomic-embed-text:latest",
}
_ST_FALLBACK = "paraphrase-multilingual-MiniLM-L12-v2"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._st = None            # sentence-transformers (lazy)
        self._ollama_model = None  # nome do modelo Ollama, se em uso
        name = (model_name or "").strip()
        want_ollama = name.startswith("ollama:") or name in _OLLAMA_EMBED
        ol = name.split("ollama:", 1)[-1] if want_ollama else ""
        if want_ollama and self._ollama_ok(ol):
            self._ollama_model = ol
        else:
            # Pediu Ollama mas indisponível -> cai para o ST multilíngue (CPU).
            self._load_st(_ST_FALLBACK if want_ollama else name)

    # -- backend Ollama --------------------------------------------------------
    # V13.3: HTTP direto via requests em vez do pacote `ollama` -- o import do
    # pacote (httpx etc.) custava ~2s de boot por processo para o que e um POST
    # trivial. keep_alive explicito mantem o bge-m3 residente na GPU (senao o
    # default do servidor pode descarrega-lo entre roteamentos).
    @staticmethod
    def _embed_http(model: str, prompt: str) -> dict:
        import requests
        host = (os.environ.get("OLLAMA_HOST")
                or "http://localhost:11434").rstrip("/")
        r = requests.post(host + "/api/embeddings",
                          json={"model": model, "prompt": prompt,
                                "keep_alive": os.environ.get(
                                    "OLLAMA_KEEP_ALIVE", "2h")},
                          timeout=60)
        r.raise_for_status()
        return r.json()

    @classmethod
    def _ollama_ok(cls, model: str) -> bool:
        """Probe único no init: o Ollama responde embeddings p/ este modelo?"""
        try:
            r = cls._embed_http(model, "ok")
            return bool(r and r.get("embedding"))
        except Exception:
            return False

    def _ollama_embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            r = self._embed_http(self._ollama_model, t or " ")
            out.append([float(x) for x in r["embedding"]])
        return out

    # -- backend sentence-transformers (fallback CPU) --------------------------
    def _load_st(self, name: str):
        from sentence_transformers import SentenceTransformer  # lazy
        self._st = SentenceTransformer(name)
        self._ollama_model = None
        self.model_name = name

    # -- API pública -----------------------------------------------------------
    def embed_chunks(self, chunks) -> list[list[float]]:
        texts = [c.text for c in chunks]
        if self._ollama_model:
            return self._ollama_embed(texts)
        return self._st.encode(texts, show_progress_bar=True).tolist()

    def embed_query(self, query: str) -> list[float]:
        if self._ollama_model:
            return self._ollama_embed([query])[0]
        return self._st.encode([query])[0].tolist()
