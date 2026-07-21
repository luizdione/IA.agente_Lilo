"""shared/models.py — Fonte ÚNICA dos modelos padrão do LILO.

Antes, os defaults de modelo estavam TRIPLICADOS (MODELS em llm_client,
TIER_MODELS em policy, VILLA_MODELS em villa_lobos) e ainda repetidos como
2º argumento de vários `.get()`/`getenv` espalhados por dashboard e agents/*.
Trocar de modelo exigia editar ~7 arquivos. Agora tudo lê daqui.

Como trocar de modelo:
  1. RECOMENDADO — edite o `.env` (`OLLAMA_MODEL`, `OLLAMA_MODEL_PLAN`, ...):
     vence sobre os defaults abaixo, sem tocar em código.
  2. Ou edite `_DEFAULTS` abaixo (afeta quem não tem a var no `.env`).

Matriz padrão (RTX 3060 12GB, jul/2026):
  chat         gemma3:12b                 geral/orquestrador/reporter (PT-BR forte)
  code         qwen2.5-coder:14b          leitura/worker de código (cabe em 12GB)
  plan         qwen3:14b                  planner/reasoning (modo thinking)
  autocomplete qwen2.5-coder:7b-instruct  SQL/autocomplete rápido
  embed        mxbai-embed-large:latest   RAG. Upgrade: `bge-m3` (multilíngue PT+EN),
                                          mas TROCAR EXIGE RE-INDEXAR data/scholar_brain/
  worker_cloud gpt-oss:120b-cloud         conhecimento factual via Ollama Cloud (0 VRAM)
"""
from __future__ import annotations

import os

from shared.utils import get_env

# ── Defaults canônicos — edite AQUI ou (melhor) no .env ─────────────────────
_DEFAULTS = {
    "chat":         "gemma3:12b",
    "code":         "qwen2.5-coder:14b",
    "plan":         "qwen3:14b",
    "autocomplete": "qwen2.5-coder:7b-instruct",
    "embed":        "mxbai-embed-large:latest",
}
_ENV_VARS = {
    "chat":         "OLLAMA_MODEL",
    "code":         "OLLAMA_MODEL_CODE",
    "plan":         "OLLAMA_MODEL_PLAN",
    "autocomplete": "OLLAMA_MODEL_FAST",
    "embed":        "OLLAMA_MODEL_EMBED",
}


def resolve() -> dict:
    """Resolve a matriz de modelos a partir do .env (fallback nos _DEFAULTS)."""
    return {role: get_env(_ENV_VARS[role], default)
            for role, default in _DEFAULTS.items()}


MODELS = resolve()
DEFAULT_MODEL = MODELS["chat"]

# Modelo cloud de conhecimento (worker geral, paper, docgen, scholar, skillsmith).
# Override global via LILO_CLOUD_MODEL; cada agente ainda pode ter o seu próprio.
WORKER_CLOUD = os.getenv("LILO_CLOUD_MODEL", "gpt-oss:120b-cloud")
