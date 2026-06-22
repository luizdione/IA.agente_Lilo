"""
verify/reranker.py -- Cross-encoder local para triagem de entailment (claim x chunk).

Usa sentence-transformers CrossEncoder (mesma stack já instalada) -> evita o conflito
peft/transformers do FlagEmbedding. Modelo padrão: mmarco-mMiniLMv2 (multilíngue, leve,
CPU-friendly). Para máxima qualidade: SCHOLAR_RERANKER_MODEL=BAAI/bge-reranker-v2-m3.
"""
from __future__ import annotations
import math

from ..config import RERANKER_MODEL


class BgeReranker:
    """Reranker via CrossEncoder. score(claim, chunk) -> 0..1."""

    def __init__(self, model_name: str = RERANKER_MODEL, device: str | None = None):
        from sentence_transformers import CrossEncoder  # lazy
        self._model = CrossEncoder(model_name, max_length=512, device=device)

    def score(self, claim_text: str, chunk_text: str) -> float:
        raw = float(self._model.predict([(claim_text, chunk_text)])[0])
        # alguns cross-encoders já devolvem 0..1; outros, logits -> sigmoide idempotente
        return raw if 0.0 <= raw <= 1.0 else 1.0 / (1.0 + math.exp(-raw))
