"""
shared/exec_mode.py — Modos de execução do LILO (estilo Claude). V14.
====================================================================
Quatro modos que controlam quanta confirmação o LILO pede antes de AGIR
(escrever arquivos, rodar shell/python):

  - "plan"         : só planeja/responde; NÃO executa ações de escrita/exec.
  - "ask"          : confirma TODA ação de risco antes de executar.
  - "accept_edits" : escrita de arquivo passa direto; shell/python confirmam.
  - "auto"         : executa tudo sem pedir (comportamento histórico = DEFAULT).

Política "confirmar só ações de RISCO" (escolha do usuário, 2026-06-12): risco =
run_shell, run_python e escrita FORA da allow-list. Escrita dentro da allow-list
é confirmada apenas no modo "ask"; em "accept_edits"/"auto" passa.

Mecânica de confirmação (para o dashboard Streamlit, stateful): a ação de risco
chama `gate(kind, preview)`. Se precisa de confirmação e não há um "grant"
pendente, devolve uma string `CONFIRM_PREFIX + preview` (a ação NÃO executa);
o dashboard detecta o prefixo, mostra um botão e, ao confirmar, chama
`grant_once()` e re-executa. Default "auto" => gate sempre libera (None).
"""

import hashlib
import os

MODES = ("plan", "ask", "accept_edits", "auto")
CONFIRM_PREFIX = "[[LILO_CONFIRMAR]] "
BLOCK_PREFIX = "[[LILO_PLANO]] "

# Estado do processo (dashboard + agentes vivem no mesmo processo Python).
_MODE = os.getenv("LILO_EXEC_MODE", "auto").lower()
if _MODE not in MODES:
    _MODE = "auto"
_GRANT = False  # autorização one-shot concedida pelo usuário
_SCOPED_GRANTS: set = set()  # grants one-shot ESCOPADOS por token (hash do cmd)

# V15 (deferred): PLANO APROVAVEL (estilo Claude Code "plan -> revisar -> aprovar
# -> executar"). No modo 'plan', cada acao bloqueada e ACUMULADA aqui; o usuario
# revisa o plano inteiro e aprova de uma vez (approve_plan) em vez de confirmar
# acao-a-acao. Estado de processo (single-user); a isolacao multi-sessao via
# ContextVar foi avaliada e descartada -- risco de quebrar o rerun do Streamlit
# sem beneficio real p/ um app pessoal, e o vazamento de grant do git ja e
# evitado pelos grants ESCOPADOS (scope_token/grant_scoped).
_PENDING_PLAN: list = []   # [{kind, preview}] acumulado no modo plan
_PLAN_APPROVED = False     # quando True, o modo plan passa a EXECUTAR


def set_mode(mode: str) -> str:
    global _MODE
    m = (mode or "").lower()
    if m in MODES:
        _MODE = m
    return _MODE


def get_mode() -> str:
    return _MODE


def grant_once() -> None:
    """Concede autorização para a PRÓXIMA ação de risco (consumida por gate)."""
    global _GRANT
    _GRANT = True


def scope_token(text: str) -> str:
    """Token curto e deterministico (hash) de um comando, p/ grant escopado."""
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:16]


def grant_scoped(token: str) -> None:
    """Concede grant one-shot ESCOPADO a um token (hash do cmd). Usado p/
    git_write: confirmar UM commit/push NAO libera outros (a skill git_dione e
    multi-repo). Skills podem chamar grant_scoped(scope_token(cmd)) antes de
    executar a operacao git que o usuario pediu explicitamente."""
    if token:
        _SCOPED_GRANTS.add(token)


def _record_plan(kind: str, preview: str) -> None:
    """Acumula uma acao bloqueada no plano (modo plan), sem duplicar a ultima."""
    item = {"kind": kind, "preview": (preview or "")[:300]}
    if not _PENDING_PLAN or _PENDING_PLAN[-1] != item:
        _PENDING_PLAN.append(item)


def pending_plan() -> list:
    """Acoes acumuladas no modo plan (para o dashboard exibir e aprovar)."""
    return list(_PENDING_PLAN)


def clear_plan() -> None:
    """Zera o plano acumulado e a aprovacao (chamar a cada novo prompt)."""
    global _PLAN_APPROVED
    _PENDING_PLAN.clear()
    _PLAN_APPROVED = False


def approve_plan() -> None:
    """Aprova o plano: as proximas chamadas de gate() no modo plan EXECUTAM
    (o dashboard reenvia o mesmo prompt apos isto). Cobre tambem git_write
    listado no plano (o usuario ja viu e aprovou)."""
    global _PLAN_APPROVED
    _PLAN_APPROVED = True


def _is_risk(kind: str) -> bool:
    # write dentro da allow-list NÃO é "risco" pela política; o desktop sinaliza
    # escrita fora da allow-list como "write_outside". git_write (commit/push) e
    # sempre risco, tratado a parte em gate() (sensivel ate em 'auto').
    return kind in ("shell", "python", "write_outside", "git_write")


def gate(kind: str, preview: str = "", *, token: str = None) -> str | None:
    """Retorna None se a ação pode executar AGORA; senão uma string de
    bloqueio/confirmação (a ação NÃO deve ser executada).

    kind: "write" | "write_outside" | "shell" | "python" | "git_write".
    token: para git_write, o scope_token(cmd) -> grant escopado ao comando.
    """
    global _GRANT
    mode = _MODE
    # git_write (commit/push/reset --hard/--force): SEMPRE sensivel, ATE em
    # 'auto' -> never-commit-unless-asked. Aceita grant ESCOPADO (token, p/
    # skills como git_dione) OU o one-shot do botao (compat dashboard). O
    # one-shot e consumido por acao, limitando push acidental multi-repo.
    if kind == "git_write":
        if token and token in _SCOPED_GRANTS:
            _SCOPED_GRANTS.discard(token)
            return None
        if _GRANT:
            _GRANT = False
            return None
        if mode == "plan":
            if _PLAN_APPROVED:        # plano revisado e aprovado -> executa
                return None
            _record_plan(kind, preview)
            return (BLOCK_PREFIX + "Modo PLANEJAMENTO: git nao executado "
                    "(commit/push).\nPrévia: %s" % preview[:300])
        return (CONFIRM_PREFIX + "git altera o repo (commit/push/reset). "
                "Confirme explicitamente (never-commit-unless-asked).\n"
                "Prévia: %s" % preview[:300])
    if mode == "auto":
        return None
    if mode == "plan":
        if _PLAN_APPROVED:            # plano revisado e aprovado -> executa
            return None
        # planejamento: acumula a acao no plano e nao executa.
        _record_plan(kind, preview)
        return (BLOCK_PREFIX + "Modo PLANEJAMENTO: a ação '%s' não foi "
                "executada (acumulada no plano). Aprove o plano para "
                "executar.\nPrévia: %s" % (kind, preview[:300]))
    # ask / accept_edits
    if mode == "accept_edits" and kind == "write":
        return None  # edição dentro da allow-list passa
    risk = _is_risk(kind) or (mode == "ask" and kind == "write")
    if not risk:
        return None
    if _GRANT:                     # usuário confirmou esta ação
        _GRANT = False
        return None
    return (CONFIRM_PREFIX + "Confirma a ação '%s'?\nPrévia: %s" % (
        kind, preview[:300]))


def is_confirm(text: str) -> bool:
    return isinstance(text, str) and text.startswith(CONFIRM_PREFIX)


def is_block(text: str) -> bool:
    return isinstance(text, str) and text.startswith(BLOCK_PREFIX)
