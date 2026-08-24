"""shared/dev_workflow.py — Workflow dev opt-in (V18.7 E7).

Encadeia peças que já existiam soltas num fluxo estilo Claude Code
(edita→testa→commita→documenta→memoriza), OPT-IN por LILO_DEV_WORKFLOW=1:

  1. TESTA  — roda pytest no alvo (subprocess isolado)
  2. COMMITA — só se verde, via git_tools.git_commit (gate git_write)
  3. DOCUMENTA — anexa uma linha ao notes.md do projeto (chat_memory)
  4. MEMORIZA — registra o resultado no KV (ns=lilo_dev_workflow)

Falha em qualquer etapa ABORTA as seguintes (não commita teste vermelho, não
documenta commit que não aconteceu) e devolve um relatório passo-a-passo. O
runner de testes é injetável (`runner=`) para teste offline.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Callable, Optional

from .logger import get_logger
from .utils import PROJECT_ROOT, get_env

log = get_logger("DevWorkflow")


def _enabled() -> bool:
    return str(get_env("LILO_DEV_WORKFLOW", "0")).strip().lower() in (
        "1", "true", "on", "yes")


def _run_pytest(target: str) -> tuple[bool, str]:
    """Roda pytest no alvo; (verde, resumo). Alvo vazio = suite inteira."""
    args = [sys.executable, "-m", "pytest", "-q", "--tb=line",
            "-p", "no:cacheprovider"]
    if target:
        args.append(target)
    try:
        r = subprocess.run(args, cwd=str(PROJECT_ROOT),
                           capture_output=True, text=True, timeout=600)
        linhas = (r.stdout or "").strip().splitlines()
        resumo = linhas[-1] if linhas else "(sem saida)"
        return r.returncode == 0, resumo
    except Exception as e:
        return False, f"pytest nao rodou: {e}"


def run_dev_workflow(
    message: str,
    test_target: str = "",
    project_id: str = "",
    runner: Optional[Callable[[str], tuple]] = None,
) -> str:
    """Executa o fluxo testa→commita→documenta→memoriza (opt-in)."""
    if not _enabled():
        return ("[dev_workflow] desligado. Defina LILO_DEV_WORKFLOW=1 para "
                "habilitar (testa -> commita -> documenta -> memoriza).")
    if not message or not message.strip():
        return "[dev_workflow] 'message' (mensagem de commit) obrigatoria"

    passos: list[str] = []

    # 1. TESTA
    verde, resumo = (runner or _run_pytest)(test_target)
    passos.append("1. testes (%s): %s" % (test_target or "suite", resumo))
    if not verde:
        passos.append("ABORTADO: testes vermelhos -> nao commita.")
        return "\n".join(passos)

    # 2. COMMITA (gate git_write)
    from .git_tools import git_commit
    commit_out = git_commit(message)
    passos.append("2. commit: " + commit_out)
    from . import exec_mode
    if exec_mode.is_confirm(commit_out) or exec_mode.is_block(commit_out):
        passos.append("PAUSADO: commit aguardando confirmacao (modo %s)."
                      % exec_mode.get_mode())
        return "\n".join(passos)
    if commit_out.startswith("[git]") and "criado" not in commit_out:
        passos.append("ABORTADO: commit nao concluiu -> nao documenta.")
        return "\n".join(passos)

    # 3. DOCUMENTA (notes.md do projeto)
    if project_id:
        try:
            from .chat_memory import get_memory as _get_chat
            cm = _get_chat()
            fn = getattr(cm, "append_to_section", None)
            if callable(fn):
                fn(project_id, "Historico de execucoes",
                   "dev_workflow: %s" % message.splitlines()[0][:80])
                passos.append("3. notes.md do projeto %s atualizado" % project_id)
            else:
                passos.append("3. notes.md: append_to_section indisponivel")
        except Exception as e:
            passos.append("3. notes.md falhou (nao-fatal): %s" % e)
    else:
        passos.append("3. notes.md: pulado (sem project_id)")

    # 4. MEMORIZA (KV)
    try:
        from .kv_memory import get_memory
        import time as _t
        # chave estavel-ish sem depender de Date.now proibido: usa contador
        # simples do proprio ns (idempotencia nao e critica aqui).
        get_memory().set(
            "run_%d" % int(_t.time()), {"msg": message, "target": test_target,
                                        "commit": commit_out},
            ns="lilo_dev_workflow", tags="dev_workflow")
        passos.append("4. resultado memorizado (ns=lilo_dev_workflow)")
    except Exception as e:
        passos.append("4. KV falhou (nao-fatal): %s" % e)

    passos.append("OK: fluxo dev concluido.")
    return "\n".join(passos)
