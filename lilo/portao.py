"""Portao de permissoes do LILO v13 — 4 modos, estado POR SESSAO, sem globals.

Herda do exec_mode.py do legado os modos (plan/ask/accept_edits/auto), o
*never-commit-unless-asked* (git_write sensivel ate em auto) e o grant
escopado por hash de comando. Redesenha o resto:

- `decidir()` e funcao PURA sobre um `Permissoes` explicito (o legado usava
  estado global de modulo, que vazava entre sessoes).
- A confirmacao acontece NO PONTO da tool call (o executor pergunta e segue
  com o resultado ou com [NEGADO]) — o legado re-executava o pedido inteiro.
- Grants sempre ESCOPADOS: write/write_outside por kind; shell e git_write
  pelo hash do comando exato. O legado tinha um booleano solto em que
  confirmar UMA acao liberava a PROXIMA, qualquer que fosse.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

MODOS = ("plan", "ask", "accept_edits", "auto")

# Decisoes possiveis do portao
PERMITIR = "permitir"
CONFIRMAR = "confirmar"
PLANO = "plano"


def token_comando(cmd: str) -> str:
    """Hash curto e estavel do comando exato (grant escopado)."""
    return hashlib.sha256(cmd.strip().encode("utf-8", "replace")).hexdigest()[:16]


@dataclass
class Permissoes:
    """Estado de permissao de UMA sessao/conversa."""
    modo: str = "ask"
    grants_kind: set = field(default_factory=set)   # {"write", "write_outside"}
    grants_cmd: set = field(default_factory=set)    # tokens de comandos exatos
    plano: list = field(default_factory=list)       # [(kind, preview)] no modo plan

    def trocar_modo(self, novo: str) -> bool:
        if novo not in MODOS:
            return False
        self.modo = novo
        return True

    def registrar_grant(self, kind: str, token: str | None = None) -> None:
        """Resposta 't' (= sempre nesta sessao) do usuario."""
        if kind in ("write", "write_outside", "mcp"):
            self.grants_kind.add(kind)
        elif token:  # shell e git_write: SO pelo comando exato
            self.grants_cmd.add(token)


def decidir(kind: str | None, perms: Permissoes,
            token: str | None = None) -> str:
    """PERMITIR | CONFIRMAR | PLANO para uma acao de tipo `kind`.

    kind None = leitura (sempre livre). Ordem importa: git_write vem ANTES
    do modo — nem `auto` commita sem confirmacao (ou grant do comando exato).
    """
    if kind is None:
        return PERMITIR

    if kind == "git_write":
        if token and token in perms.grants_cmd:
            return PERMITIR
        return PLANO if perms.modo == "plan" else CONFIRMAR

    if perms.modo == "auto":
        return PERMITIR
    if perms.modo == "plan":
        return PLANO
    if perms.modo == "accept_edits" and kind == "write":
        return PERMITIR

    # modo ask (e residuos do accept_edits: shell/write_outside)
    if kind in perms.grants_kind:
        return PERMITIR
    if token and token in perms.grants_cmd:
        return PERMITIR
    return CONFIRMAR
