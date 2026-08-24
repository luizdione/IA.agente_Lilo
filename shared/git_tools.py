"""shared/git_tools.py — Tools git dedicadas (V18.7 E7).

Promove git de "string opaca no run_shell" para tools TIPADAS (padrão-ouro
Claude Code: ações que precisam de gate/render viram tools dedicadas).
git_status/git_diff são somente-leitura (seguras, paralelizáveis);
git_commit passa pelo gate `git_write` do exec_mode (never-commit-unless-
asked) — a CHAMADA EXPLÍCITA da tool é a autorização (padrão git_dione),
exceto no modo `plan`, onde o commit é deferido ao plano.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from .logger import get_logger
from .utils import PROJECT_ROOT

log = get_logger("GitTools")

_MAX_DIFF_CHARS = 8000


def _git(args: list, cwd=None, timeout: int = 20):
    return subprocess.run(
        ["git"] + args, cwd=str(cwd or PROJECT_ROOT),
        capture_output=True, text=True, timeout=timeout)


def _is_repo(cwd=None) -> bool:
    try:
        r = _git(["rev-parse", "--is-inside-work-tree"], cwd)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def git_status(cwd=None) -> str:
    """Estado da árvore (branch + arquivos modificados). Somente leitura."""
    if not _is_repo(cwd):
        return "[git] nao e um repositorio git"
    try:
        r = _git(["status", "--short", "--branch"], cwd)
        return r.stdout.strip() or "[git] arvore limpa"
    except Exception as e:
        return f"[git] erro no status: {e}"


def git_diff(staged: bool = False, cwd=None, max_chars: int = _MAX_DIFF_CHARS) -> str:
    """Diff da árvore (ou staged). Somente leitura; truncado p/ nao inflar."""
    if not _is_repo(cwd):
        return "[git] nao e um repositorio git"
    try:
        args = ["diff"] + (["--staged"] if staged else [])
        r = _git(args, cwd)
        out = r.stdout
        if not out.strip():
            return "[git] sem diff" + (" staged" if staged else "")
        if len(out) > max_chars:
            out = out[:max_chars] + "\n... (diff truncado)"
        return out
    except Exception as e:
        return f"[git] erro no diff: {e}"


def git_commit(message: str, add_all: bool = True, cwd=None) -> str:
    """Cria um commit (gate `git_write`). A chamada explicita da tool e a
    autorizacao (padrao git_dione); no modo `plan` o commit e deferido."""
    if not message or not message.strip():
        return "[git] mensagem de commit obrigatoria"
    if not _is_repo(cwd):
        return "[git] nao e um repositorio git"
    from . import exec_mode
    preview = "git commit -m %r" % message[:100]
    if exec_mode.get_mode() == "plan":
        # respeita o planejamento: acumula e bloqueia (nao commita).
        blocked = exec_mode.gate("git_write", preview)
        if blocked:
            return blocked
    else:
        tok = exec_mode.scope_token(preview)
        exec_mode.grant_scoped(tok)  # chamada explicita = autorizacao
        blocked = exec_mode.gate("git_write", preview, token=tok)
        if blocked:  # fail-safe (nao deveria ocorrer com o grant)
            return blocked
    try:
        if add_all:
            _git(["add", "-A"], cwd)
        r = _git(["commit", "-m", message], cwd)
        if r.returncode != 0:
            saida = (r.stdout + r.stderr).strip()
            if "nothing to commit" in saida:
                return "[git] nada para commitar"
            return "[git] commit falhou: " + saida[:300]
        # hash curto do commit recem-criado
        h = _git(["rev-parse", "--short", "HEAD"], cwd).stdout.strip()
        return "[git] commit %s criado: %s" % (h, message.splitlines()[0][:80])
    except Exception as e:
        return f"[git] erro no commit: {e}"


def current_branch(cwd=None) -> Optional[str]:
    try:
        r = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        return r.stdout.strip() or None
    except Exception:
        return None
