"""Configuracao do LILO v13 — envs lidas AO VIVO (nada congelado no import).

Licao do legado: a allow-list era avaliada uma vez no import do modulo e
nunca mais (agents/desktop/agent.py:66 do v12) — aqui toda leitura e uma
funcao, entao .env carregado depois, testes com monkeypatch e mudancas de
ambiente funcionam sem reload.
"""
from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def load_env(caminho: Path | None = None) -> None:
    """Carrega o .env da raiz SEM sobrescrever env ja setada (heranca do
    shared/utils.py do legado). python-dotenv se existir; fallback manual."""
    env = caminho or (RAIZ / ".env")
    try:
        from dotenv import load_dotenv
        load_dotenv(env, override=False)
        return
    except ImportError:
        pass
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def get_env(nome: str, default: str = "") -> str:
    return os.environ.get(nome, default)


def _int(nome: str, default: int) -> int:
    try:
        return int(get_env(nome, str(default)))
    except ValueError:
        return default


def _float(nome: str, default: float) -> float:
    try:
        return float(get_env(nome, str(default)))
    except ValueError:
        return default


# --- Conexao/modelo ---------------------------------------------------------
def ollama_host() -> str:
    return get_env("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def timeout_s() -> float:
    return _float("LLM_TIMEOUT", 300.0)


def keep_alive() -> str:
    return get_env("OLLAMA_KEEP_ALIVE", "2h")


def modelo() -> str:
    return get_env("LILO_MODEL", "qwen2.5-coder:14b")


def modelo_fast() -> str:
    return get_env("LILO_MODEL_FAST", "qwen2.5-coder:7b-instruct")


def num_ctx() -> int:
    return _int("LILO_NUM_CTX", 16384)


def temperatura() -> float:
    return _float("LILO_TEMP", 0.2)


def max_tokens() -> int:
    return _int("LILO_MAX_TOKENS", 4096)


def retries() -> int:
    return _int("LILO_LLM_RETRIES", 2)


def backoff_base() -> float:
    return _float("LILO_LLM_BACKOFF", 1.5)


# --- Agente -----------------------------------------------------------------
def modo_inicial() -> str:
    m = get_env("LILO_MODE", "ask").strip().lower()
    return m if m in ("plan", "ask", "accept_edits", "auto") else "ask"


def max_iters() -> int:
    return _int("LILO_MAX_ITERS", 25)


def allow_list() -> list[Path]:
    """Diretorios que as tools de arquivo podem tocar. Separador ';' no
    Windows, ':' no Unix. Vazio -> [cwd] (o projeto em que o LILO foi
    aberto). Avaliada a cada chamada — nunca congelada."""
    bruto = get_env("LILO_ALLOW", "")
    sep = ";" if os.name == "nt" else ":"
    raizes: list[Path] = []
    for parte in bruto.split(sep):
        parte = parte.strip()
        if not parte:
            continue
        p = Path(parte).expanduser()
        try:
            p = p.resolve()
        except OSError:
            continue
        if p.exists():
            raizes.append(p)
    return raizes or [Path.cwd().resolve()]


# --- Dados (SEMPRE fora do repo/OneDrive — licao kv_memory do legado) -------
def dir_dados() -> Path:
    if os.name == "nt":
        base = Path(get_env("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        d = base / "LILO"
    else:
        d = Path.home() / ".local" / "share" / "lilo"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sessions_db() -> Path:
    override = get_env("LILO_SESSIONS_DB", "")
    return Path(override) if override else dir_dados() / "sessions.db"
