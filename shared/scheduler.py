"""
shared/scheduler.py -- Executor de tarefas agendadas do Cowork (V15 FASE 5).
============================================================================
Fecha a maior promessa-nao-cumprida vs Claude Cowork: as tarefas agendadas
(SKILL.md lidas por dashboard_cowork.list_scheduled) eram apenas EXIBIDAS, nunca
executadas. Este modulo as EXECUTA -- com guardas fortes, por ser o ponto de
maior risco do projeto (execucao autonoma sem usuario presente):

  - DEFAULT-OFF: so executa de fato com LILO_ENABLE_SCHEDULER=1 E dry_run=False.
    Sem isso, faz DRY-RUN (apenas lista o que rodaria).
  - Perfil 'cowork' FORCADO: local-only (allow_cloud=false), SEM run_shell/
    run_python no conjunto de tools -> a tarefa nao tem como executar acoes de
    risco mesmo sem supervisao.
  - exec_mode 'ask': qualquer acao sensivel que escapasse e BLOQUEADA (nao ha
    quem confirme) em vez de executada.
  - Teto de tarefas por corrida (max_tasks) + registro de saida/custo em
    KVMemory (ns 'lilo_tasks') para revisao posterior pelo dono.
  - NAO inicia thread em background: e chamado SOB DEMANDA (scripts/
    run_scheduler.py via cron/Task Scheduler externo, ou botao no dashboard).
    Assim nao existe loop autonomo sempre-ligado.

Frontmatter reconhecido no SKILL.md (alem de name/description):
    schedule: hourly | daily | weekly | manual   (default manual = nunca auto)
    enabled:  true | false                        (default true)
"""

import os
import time

_INTERVALS = {"hourly": 3600, "daily": 86400, "weekly": 604800}
_NS = "lilo_tasks"


def enabled() -> bool:
    """Execucao real so com LILO_ENABLE_SCHEDULER=1 (default desligado)."""
    return os.getenv("LILO_ENABLE_SCHEDULER", "0").strip().lower() not in (
        "0", "false", "no", "off", "")


def _parse_meta(text: str):
    """Extrai (schedule, enabled) do frontmatter YAML simples do SKILL.md."""
    schedule, en = "manual", True
    if text.startswith("---"):
        block = text.split("---", 2)
        if len(block) >= 3:
            for line in block[1].splitlines():
                if ":" not in line:
                    continue
                k, _, v = line.partition(":")
                k, v = k.strip().lower(), v.strip().lower()
                if k in ("schedule", "cron", "when"):
                    schedule = v
                elif k == "enabled":
                    en = v not in ("false", "no", "0", "off")
    return schedule, en


def list_tasks():
    """Tarefas agendadas (reusa a descoberta do dashboard_cowork) + schedule."""
    try:
        from dashboard_cowork import list_scheduled
    except Exception:
        return []
    out = []
    for t in list_scheduled():
        try:
            with open(t["path"], encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
        except Exception:
            continue
        schedule, en = _parse_meta(txt)
        out.append({**t, "schedule": schedule, "enabled": en})
    return out


def _last_run_key(name: str) -> str:
    return "last_run::" + name


def is_due(task: dict, now: float = None) -> bool:
    """True se a tarefa tem intervalo (hourly/daily/weekly), esta enabled e o
    intervalo ja decorreu desde a ultima execucao (last_run em KV). 'manual'
    nunca e 'due' automaticamente."""
    if not task.get("enabled", True):
        return False
    interval = _INTERVALS.get(task.get("schedule", "manual"))
    if not interval:
        return False
    now = now if now is not None else time.time()
    last = 0.0
    try:
        from shared.kv_memory import get_memory
        raw = get_memory().get(_last_run_key(task["name"]), ns=_NS)
        last = float(raw) if raw else 0.0
    except Exception:
        last = 0.0
    return (now - last) >= interval


def run_task(task: dict, dry_run: bool = True, now: float = None) -> dict:
    """Executa UMA tarefa sob perfil cowork + exec_mode ask, registrando a saida
    em KV. Em dry_run, apenas reporta que rodaria (nao chama LLM)."""
    now = now if now is not None else time.time()
    if dry_run:
        return {"name": task["name"], "schedule": task.get("schedule"),
                "dry_run": True, "would_run": True}
    # Forca perfil local-only (sem shell/python) e modo ask (bloqueia risco).
    os.environ.setdefault("LILO_SERVER_PROFILE", "cowork")
    try:
        from shared import exec_mode as _xm
        _xm.set_mode("ask")
    except Exception:
        pass
    result = ""
    try:
        from lilo import route
        result = route(task.get("prompt", task["name"]),
                       context={"exec_mode": "ask", "scheduled": True,
                                "response_style": "concise"})
    except Exception as e:
        result = "[scheduler] erro ao executar '%s': %s" % (task["name"], e)
    # Registra ultima execucao + saida (para revisao do dono).
    try:
        from shared.kv_memory import get_memory
        kv = get_memory()
        kv.set(_last_run_key(task["name"]), str(now), ns=_NS, tags="scheduler")
        kv.set("result::%s::%d" % (task["name"], int(now)),
               (result or "")[:4000], ns=_NS, tags="scheduled,result")
    except Exception:
        pass
    return {"name": task["name"], "dry_run": False, "chars": len(result or "")}


def run_due_tasks(dry_run: bool = True, max_tasks: int = 5,
                  now: float = None) -> dict:
    """Ponto de entrada. Roda as tarefas 'due' (ate max_tasks). Execucao real
    exige dry_run=False E LILO_ENABLE_SCHEDULER=1; senao volta a DRY-RUN."""
    now = now if now is not None else time.time()
    if not dry_run and not enabled():
        return {"now": now, "dry_run": True, "blocked": True,
                "reason": "LILO_ENABLE_SCHEDULER nao habilitado (use =1 p/ executar)",
                "results": []}
    due = [t for t in list_tasks() if is_due(t, now)][:max(1, max_tasks)]
    results = [run_task(t, dry_run=dry_run, now=now) for t in due]
    return {"now": now, "dry_run": dry_run, "due_count": len(due),
            "results": results}
