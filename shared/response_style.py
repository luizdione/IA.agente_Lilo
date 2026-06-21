"""
shared/response_style.py -- Eixo de ESTILO de resposta (V15 FASE 2).
====================================================================
get_style_block(name) devolve o bloco de texto do estilo, para concatenar ao
system prompt das SAIDAS via prompt_blocks.compose_system(style_block=...).

Fonte: config/styles.yaml (hot-reload por mtime, padrao copiado de
shared/server_profile._load_yaml_policies). Resolucao do estilo ativo:
    nome explicito > env LILO_RESPONSE_STYLE > 'default'.
Aceita rotulos PT da UI (Padrao/Conciso/Didatico/Formal).
"""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_STYLES_YAML = _ROOT / "config" / "styles.yaml"
_CACHE = {"mtime": None, "styles": {}}

# Fallback embarcado se o YAML sumir: so o conciso (o de maior valor p/ a meta
# "minimo de tokens"); os demais caem em '' (= comportamento atual).
_FALLBACK = {
    "default": "",
    "concise": ("Estilo CONCISO: minimo de tokens mantendo qualidade. Sem "
                "preambulo/postambulo; escale o comprimento a complexidade. "
                "NAO-DEGRADACAO: codigo/tabelas/citacoes/artefatos plenos. "
                "ESCAPE: se pedirem resposta longa, ignore a concisao."),
    "explanatory": "",
    "formal": "",
}

_ALIASES = {
    "padrao": "default", "padrão": "default", "default": "default",
    "conciso": "concise", "concise": "concise",
    "didatico": "explanatory", "didático": "explanatory",
    "explicativo": "explanatory", "explanatory": "explanatory",
    "formal": "formal",
}


def _load() -> dict:
    if not _STYLES_YAML.exists():
        return dict(_FALLBACK)
    try:
        mtime = _STYLES_YAML.stat().st_mtime
        if _CACHE["mtime"] == mtime and _CACHE["styles"]:
            return _CACHE["styles"]
        import yaml as _yaml
        with _STYLES_YAML.open("r", encoding="utf-8") as fh:
            data = _yaml.safe_load(fh) or {}
        styles = {str(k): (v or "") for k, v in data.items()}
        styles.setdefault("default", "")
        _CACHE["styles"] = styles
        _CACHE["mtime"] = mtime
        return styles
    except Exception:
        return dict(_FALLBACK)


def available() -> list:
    """Nomes canonicos de estilo disponiveis (p/ a UI)."""
    return ["default", "concise", "explanatory", "formal"]


def get_style_block(name: str = None) -> str:
    """Bloco de estilo resolvido. '' (no-op) para 'default' ou nome invalido."""
    raw = (name or os.getenv("LILO_RESPONSE_STYLE") or "default")
    key = _ALIASES.get(str(raw).strip().lower(), str(raw).strip().lower())
    return (_load().get(key) or "").strip()
