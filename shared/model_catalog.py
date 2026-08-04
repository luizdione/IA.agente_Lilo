"""shared/model_catalog.py — Catalogo central de modelos (V18 E1).

Fonte UNICA de metadados por modelo: provedor, janela de contexto (tokens),
capacidades, classe de latencia e custo (USD por MILHAO de tokens).

Motivacao (docs/tecnico/analise_open_agent_studio.md, item E1): os modelos
`*-cloud` (Ollama Cloud) eram usados como default por varios subagentes mas
INVISIVEIS ao Policy Engine e a telemetria; os precos Anthropic viviam
hardcoded no llm_client; e nao existia lugar para consultar contexto/latencia
de um modelo. Este modulo e ADITIVO: nenhum roteamento muda por ele —
consumidores desta fase sao telemetria (rotulo de backend do Villa), o custo
real do llm_client (QW4) e o gate de privacidade pre-cloud (E5).

Precos Anthropic conferidos em 2026-08-04 (doc oficial de pricing):
opus $5/$25, sonnet $3/$15, haiku $1/$5 por MTok (input/output).
"""
from __future__ import annotations

from dataclasses import dataclass

PROVIDER_OLLAMA = "ollama"              # local (GPU/CPU da maquina)
PROVIDER_OLLAMA_CLOUD = "ollama_cloud"  # Ollama Cloud (via daemon local)
PROVIDER_ANTHROPIC = "anthropic"        # API Claude


@dataclass(frozen=True)
class ModelInfo:
    name: str
    provider: str
    context_tokens: int = 8192
    capabilities: tuple = ("general",)
    latency_class: str = "medium"        # fast | medium | slow
    cost_in_mtok: float = 0.0            # USD/MTok input (0 = local/assinatura)
    cost_out_mtok: float = 0.0


# Precos por FAMILIA Anthropic (prefixo do model id -> (input, output) USD/MTok)
_ANTHROPIC_FAMILY_PRICES = {
    "claude-opus":   (5.00, 25.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku":  (1.00, 5.00),
}

# Modelos conhecidos (defaults do LILO). Contexto conforme a tag do modelo.
_CATALOG: dict[str, ModelInfo] = {
    # Locais (Ollama)
    "llama3.1:8b-instruct-q8_0": ModelInfo(
        "llama3.1:8b-instruct-q8_0", PROVIDER_OLLAMA, 131072,
        ("general",), "fast"),
    "qwen2.5-coder:14b": ModelInfo(
        "qwen2.5-coder:14b", PROVIDER_OLLAMA, 32768, ("code",), "medium"),
    "qwen2.5-coder:7b-instruct": ModelInfo(
        "qwen2.5-coder:7b-instruct", PROVIDER_OLLAMA, 32768,
        ("code", "general"), "fast"),
    "phi3:14b-medium-128k-instruct-q4_K_M": ModelInfo(
        "phi3:14b-medium-128k-instruct-q4_K_M", PROVIDER_OLLAMA, 131072,
        ("reasoning", "general"), "medium"),
    "mxbai-embed-large:latest": ModelInfo(
        "mxbai-embed-large:latest", PROVIDER_OLLAMA, 512, ("embed",), "fast"),
    # Ollama Cloud (default de villa-worker/skillsmith/docgen/review/paper)
    "gpt-oss:120b-cloud": ModelInfo(
        "gpt-oss:120b-cloud", PROVIDER_OLLAMA_CLOUD, 131072,
        ("general", "reasoning"), "medium"),
    # Anthropic (defaults do LILO via LILO_CLAUDE_*)
    "claude-haiku-4-5": ModelInfo(
        "claude-haiku-4-5", PROVIDER_ANTHROPIC, 200_000,
        ("general",), "fast", 1.00, 5.00),
    "claude-sonnet-4-5": ModelInfo(
        "claude-sonnet-4-5", PROVIDER_ANTHROPIC, 200_000,
        ("general", "code", "reasoning"), "medium", 3.00, 15.00),
    "claude-opus-4-5": ModelInfo(
        "claude-opus-4-5", PROVIDER_ANTHROPIC, 200_000,
        ("general", "code", "reasoning"), "slow", 5.00, 25.00),
}


def get_model_info(name) -> ModelInfo:
    """Metadados de um modelo. Match exato no catalogo; senao heuristica:
    sufixo `-cloud` -> Ollama Cloud; prefixo `claude-` -> Anthropic (preco da
    familia; familia desconhecida assume Opus — superestimar e fail-safe para
    o budget); qualquer outro nome -> Ollama local generico."""
    n = str(name or "").strip()
    if n in _CATALOG:
        return _CATALOG[n]
    if n.endswith("-cloud"):
        return ModelInfo(n, PROVIDER_OLLAMA_CLOUD, 131072,
                         ("general",), "medium")
    if n.startswith("claude-"):
        for family, (p_in, p_out) in _ANTHROPIC_FAMILY_PRICES.items():
            if n.startswith(family):
                break
        else:
            p_in, p_out = _ANTHROPIC_FAMILY_PRICES["claude-opus"]
        return ModelInfo(n, PROVIDER_ANTHROPIC, 200_000,
                         ("general", "reasoning"), "medium", p_in, p_out)
    return ModelInfo(n, PROVIDER_OLLAMA, 8192, ("general",), "medium")


def is_cloud_model(name) -> bool:
    """True quando o conteudo SAI da maquina (Anthropic ou Ollama Cloud)."""
    return get_model_info(name).provider != PROVIDER_OLLAMA


def anthropic_prices_mtok(name) -> tuple[float, float]:
    """(input, output) em USD/MTok para um modelo Claude (com fail-safe)."""
    info = get_model_info(name)
    if info.provider == PROVIDER_ANTHROPIC:
        return (info.cost_in_mtok, info.cost_out_mtok)
    return _ANTHROPIC_FAMILY_PRICES["claude-opus"]


def missing_models(configured, installed) -> list[str]:
    """Modelos LOCAIS configurados ausentes da lista `ollama list`/api/tags.

    Ignora Anthropic e Ollama Cloud (nao sao instalaveis localmente). Aceita
    match exato ou pelo nome-base antes de ':' (tags variantes)."""
    inst = {str(i).strip() for i in (installed or []) if str(i).strip()}
    base = {i.split(":")[0] for i in inst}
    out: list[str] = []
    for name in configured or []:
        info = get_model_info(name)
        if info.provider != PROVIDER_OLLAMA:
            continue
        if name in inst or str(name).split(":")[0] in base:
            continue
        out.append(name)
    return out
