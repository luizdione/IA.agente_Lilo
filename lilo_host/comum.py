"""Suporte comum da ponte: interruptor de GPU, caminhos, token e recortes."""
from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODELO = os.environ.get("LILO_MODELO", "lilo")
PORTA = int(os.environ.get("LILO_HOST_PORTA", "8790"))

# Pasta de trabalho propria da ponte: cwd padrao do grupo exec e dos temporarios.
TRABALHO = Path(os.environ.get("LILO_HOST_TRABALHO", r"E:\data\lilo\trabalho"))
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LILO"
ARQ_TOKEN = LOCAL / "host_token.txt"
ARQ_STATUS = LOCAL / "host.status.json"

# Mesmo arquivo do MCP ollama-local e do lilo.ps1: um interruptor so para toda a GPU.
ARQ_INTERRUPTOR = Path(os.environ.get("OLLAMA_DELEGATE_DIR",
                                      str(Path.home() / ".ollama_delegate"))) / "switch.json"

# Comandos que nunca rodam, em nenhum modo (herdado da v13, lilo/tools.py).
PADROES_PROIBIDOS = (
    r"rm\s+-rf\s+/(?:\s|$)", r"rm\s+-rf\s+~", r"format\s+[a-z]:",
    r"del\s+/[fsq]\s+", r":\(\)\{.*\};:", r"\bmkfs\b",
    r"\bdd\b.*\bof=/dev/", r">\s*/dev/sd[a-z]", r"\bshutdown\b", r"\breboot\b",
)


def comando_proibido(texto: str) -> str | None:
    """Padrao da deny-list que o texto contem, ou None."""
    for p in PADROES_PROIBIDOS:
        if re.search(p, texto, re.IGNORECASE):
            return p
    return None


def gpu_reservada() -> str | None:
    """Motivo da reserva se o interruptor NAO estiver em on; None se a GPU e nossa.

    Falha fechada: arquivo ilegivel ou sem campo conta como reservada. Arquivo
    ausente e o padrao do MCP ollama-local (= on). BOM e tolerado (utf-8-sig).
    """
    if not ARQ_INTERRUPTOR.exists():
        return None
    try:
        d = json.loads(ARQ_INTERRUPTOR.read_text(encoding="utf-8-sig"))
        estado = str(d.get("estado", "")).lower()
    except Exception:
        return "interruptor de GPU ilegivel (%s)" % ARQ_INTERRUPTOR
    if estado == "on":
        return None
    return str(d.get("motivo") or "GPU reservada pelo dono")


def resolver(caminho: str) -> Path:
    """Caminho absoluto, com ~ expandido; relativo resolve contra a pasta de trabalho."""
    p = Path(os.path.expandvars(str(caminho))).expanduser()
    if not p.is_absolute():
        p = TRABALHO / p
    return p


def recortar(texto: str, limite: int) -> str:
    """Corta preservando inicio e fim (logs guardam o resultado no fim)."""
    if len(texto) <= limite:
        return texto
    cabeca = int(limite * 0.7)
    cauda = limite - cabeca
    return (texto[:cabeca] + "\n\n... [meio omitido: %d caracteres] ...\n\n" % (len(texto) - limite)
            + texto[-cauda:])


def token_exec(gerar: bool = True) -> str:
    """Token do grupo exec: LILO_HOST_TOKEN, senao o arquivo local (criado se faltar)."""
    t = os.environ.get("LILO_HOST_TOKEN", "").strip()
    if t:
        return t
    if ARQ_TOKEN.exists():
        t = ARQ_TOKEN.read_text(encoding="utf-8").strip()
        if t:
            return t
    if not gerar:
        return ""
    t = secrets.token_urlsafe(32)
    ARQ_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    ARQ_TOKEN.write_text(t, encoding="utf-8")
    return t


def erro(msg: str) -> str:
    return "[ERRO] " + msg
