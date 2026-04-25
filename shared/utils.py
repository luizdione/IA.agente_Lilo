"""
shared/utils.py — Utilitários gerais compartilhados pelo LILO.
"""

import os
from pathlib import Path
from typing import Optional


# ── Raiz do projeto ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent


def load_env(env_file: Optional[Path] = None) -> None:
    """
    Carrega variáveis do .env centralizado na raiz do projeto.
    Usa python-dotenv se disponível; caso contrário, faz parsing manual.
    Idempotente: variáveis já definidas no ambiente não são sobrescritas.
    """
    env_path = env_file or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass

    # Fallback manual
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Lê variável de ambiente com fallback."""
    return os.environ.get(key, default)


def truncate(text: str, max_chars: int = 2000) -> str:
    """Trunca texto longo para uso em logs/prompts."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncado — {len(text) - max_chars} chars omitidos]"


def sanitize_query(query: str) -> str:
    """Remove caracteres problemáticos de queries do usuário."""
    return query.strip().replace("\x00", "")
