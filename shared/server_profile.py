"""shared/server_profile.py -- Perfil do servidor para roteamento adaptativo.

V9 (2026-05-22): "atuar... sempre de acordo com o setup do servidor".
V10 (2026-05-30): merge opcional de config/profiles.yaml (hot-reload).

O orquestrador Villa_Lobos consulta `get_profile_policy()` no boot para
decidir, conforme ONDE esta rodando, se prefere modelos locais (Ollama) ou
pode escalar para a nuvem (Anthropic), e qual o teto de iteracoes. Assim o
MESMO codigo se comporta diferente no Claude Desktop, no PyCharm, no Cowork
(automacao) ou no perfil bio molecular -- sem ramificacoes espalhadas.

Seleciona-se o perfil via env `LILO_SERVER_PROFILE`. Default: `desktop_dev`.
Perfis desconhecidos caem numa politica conservadora (local, sem nuvem).

V10: se `config/profiles.yaml` existir, suas policies sobrescrevem os
defaults embarcados aqui (hot-reload por mtime, zero restart). Permite
ajustar `max_iterations`, `allow_cloud`, etc. sem editar Python.
"""

import os
from pathlib import Path

ENV_VAR = "LILO_SERVER_PROFILE"
DEFAULT_PROFILE = "desktop_dev"

_PROFILES_YAML = Path(__file__).resolve().parents[1] / "config" / "profiles.yaml"
_YAML_CACHE = {"mtime": None, "policies": None, "aliases": {}, "fallback": None}

_PROFILE_POLICY_DEFAULTS = {
    "desktop_dev": {
        "prefer_local": True,
        "allow_cloud": True,
        "max_iterations": 3,
        "description": "Maquina de desenvolvimento; local primeiro, nuvem liberada.",
    },
    "pycharm_assistant": {
        "prefer_local": True,
        "allow_cloud": True,
        "max_iterations": 2,
        "description": "Assistente dentro do PyCharm; respostas rapidas, nuvem opcional.",
    },
    "claude_desktop": {
        "prefer_local": False,
        "allow_cloud": True,
        "max_iterations": 3,
        "description": "Claude Desktop (MCP/stdio); nuvem disponivel, qualidade primeiro.",
    },
    "cowork": {
        "prefer_local": True,
        "allow_cloud": False,
        "max_iterations": 2,
        "description": "Automacao Cowork sem usuario; local-only para evitar custo.",
    },
    "bio": {
        "prefer_local": True,
        "allow_cloud": False,
        "max_iterations": 2,
        "description": "Perfil bio molecular; 100% local, sem run_shell, sem custo.",
    },
    "openclaw": {
        "prefer_local": True,
        "allow_cloud": True,
        "max_iterations": 3,
        "description": "OpenClaw CLI (compat Claude Code); local primeiro, nuvem liberada.",
    },
    "claude_code": {
        "prefer_local": True,
        "allow_cloud": True,
        "max_iterations": 3,
        "description": "Claude Code CLI; local primeiro, nuvem permitida.",
    },
}

FALLBACK_POLICY = {
    "prefer_local": True,
    "allow_cloud": False,
    "max_iterations": 2,
    "description": "Perfil desconhecido; politica conservadora local-only.",
}


def _load_yaml_policies():
    """Carrega config/profiles.yaml e merge com defaults (hot-reload)."""
    if not _PROFILES_YAML.exists():
        return dict(_PROFILE_POLICY_DEFAULTS), {}, dict(FALLBACK_POLICY)
    try:
        mtime = _PROFILES_YAML.stat().st_mtime
        if _YAML_CACHE["mtime"] == mtime and _YAML_CACHE["policies"]:
            return (_YAML_CACHE["policies"],
                    _YAML_CACHE["aliases"],
                    _YAML_CACHE["fallback"])
        try:
            import yaml as _yaml
        except ImportError:
            return dict(_PROFILE_POLICY_DEFAULTS), {}, dict(FALLBACK_POLICY)
        with _PROFILES_YAML.open("r", encoding="utf-8") as fh:
            data = _yaml.safe_load(fh) or {}
        merged = dict(_PROFILE_POLICY_DEFAULTS)
        yprofiles = data.get("profiles") or {}
        if isinstance(yprofiles, dict):
            for name, conf in yprofiles.items():
                if not isinstance(conf, dict):
                    continue
                pol = conf.get("policy") or {}
                if isinstance(pol, dict) and pol:
                    base = dict(merged.get(str(name), {}))
                    base.update({k: v for k, v in pol.items()
                                 if k in ("prefer_local", "allow_cloud",
                                          "max_iterations", "description")})
                    merged[str(name)] = base
        aliases = data.get("aliases") or {}
        if not isinstance(aliases, dict):
            aliases = {}
        fb = data.get("fallback_policy") or dict(FALLBACK_POLICY)
        if not isinstance(fb, dict):
            fb = dict(FALLBACK_POLICY)
        _YAML_CACHE["policies"] = merged
        _YAML_CACHE["aliases"] = {str(k): str(v) for k, v in aliases.items()}
        _YAML_CACHE["fallback"] = fb
        _YAML_CACHE["mtime"] = mtime
        return merged, _YAML_CACHE["aliases"], fb
    except Exception:
        return dict(_PROFILE_POLICY_DEFAULTS), {}, dict(FALLBACK_POLICY)


# Expor PROFILE_POLICY (alias para compat com codigo antigo).
PROFILE_POLICY = _PROFILE_POLICY_DEFAULTS


def get_server_profile() -> str:
    """Retorna o nome do perfil ativo (env LILO_SERVER_PROFILE)."""
    raw = os.environ.get(ENV_VAR, DEFAULT_PROFILE).strip() or DEFAULT_PROFILE
    _, aliases, _ = _load_yaml_policies()
    return aliases.get(raw, raw)


def get_profile_policy(profile: str = None) -> dict:
    """Retorna a politica do perfil dado (ou do perfil ativo)."""
    policies, aliases, fallback = _load_yaml_policies()
    name = profile or get_server_profile()
    name = aliases.get(name, name)
    policy = dict(policies.get(name, fallback))
    policy["profile"] = name
    policy["known"] = name in policies
    return policy


def list_profiles() -> list:
    """Lista os nomes de perfis conhecidos (defaults + YAML)."""
    policies, _, _ = _load_yaml_policies()
    return sorted(policies.keys())


if __name__ == "__main__":
    import json as _json
    print("Perfil ativo:", get_server_profile())
    print(_json.dumps(get_profile_policy(), indent=2, ensure_ascii=False))
    print("Perfis disponiveis:", list_profiles())
