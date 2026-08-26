"""Cores ANSI do terminal — minimas e auto-desligaveis.

Ligadas so quando stdout e um TTY e LILO_CORES != 0. No Windows 10+, o
cli.main chama `os.system('')` uma vez, o truque documentado que ativa o
processamento VT no cmd.exe. Sem TTY (pipe, CI, testes) tudo vira texto puro.
"""
from __future__ import annotations

import os
import sys

_RESET = "\x1b[0m"
_CODIGOS = {
    "verde": "\x1b[32m",
    "vermelho": "\x1b[31m",
    "ciano": "\x1b[36m",
    "amarelo": "\x1b[33m",
    "dim": "\x1b[2m",
    "negrito": "\x1b[1m",
}


def ativas() -> bool:
    if os.environ.get("LILO_CORES", "1").strip().lower() in ("0", "false", "off"):
        return False
    try:
        return bool(sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


def pinta(texto: str, cor: str) -> str:
    if not ativas() or cor not in _CODIGOS:
        return texto
    return _CODIGOS[cor] + texto + _RESET


def pinta_diff(linha: str) -> str:
    """Linha de diff unificado: + verde, - vermelho, @@ ciano."""
    if linha.startswith("+"):
        return pinta(linha, "verde")
    if linha.startswith("-"):
        return pinta(linha, "vermelho")
    if linha.startswith("@@"):
        return pinta(linha, "ciano")
    return linha
