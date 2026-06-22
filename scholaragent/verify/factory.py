"""
verify/factory.py — Monta o Grounder de produção (reranker local + juiz Lilo 3.0).

Mantém as dependências pesadas fora do import do pacote: BgeReranker só baixa o
modelo quando instanciado, e o juiz só usa httpx na primeira chamada.
"""
from __future__ import annotations

from .grounding import Grounder
from .ollama_judge import make_ollama_judge
from .reranker import BgeReranker
from ..config import LLM_URL, LLM_MODEL, RERANKER_MODEL


def build_grounder(store=None, embedder=None, *,
                   model: str = LLM_MODEL,
                   reranker_model: str = RERANKER_MODEL,
                   ollama_url: str = LLM_URL,
                   use_reranker: bool = True) -> Grounder:
    """Grounder pronto para produção: juiz NLI local + reranker local + re-busca opcional.

    Se o FlagEmbedding não estiver instalado (ou use_reranker=False), o Grounder
    funciona sem reranker: a triagem cai para sobreposição de tokens (Jaccard).
    """
    reranker = None
    if use_reranker:
        try:
            reranker = BgeReranker(reranker_model)
        except Exception:
            reranker = None   # FlagEmbedding ausente -> triagem por tokens
    return Grounder(
        judge=make_ollama_judge(url=ollama_url, model=model),
        reranker=reranker,
        store=store,
        embedder=embedder,
    )
