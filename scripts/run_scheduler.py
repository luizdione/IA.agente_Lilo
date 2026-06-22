"""
scripts/run_scheduler.py -- Dispara o scheduler do Cowork SOB DEMANDA (V15 FASE 5).
================================================================================
Pensado para ser chamado por um agendador EXTERNO (Windows Task Scheduler / cron)
ou por um botao no dashboard -- NAO ha loop sempre-ligado dentro do LILO.

  Listar tarefas e quais estao 'due':   python scripts/run_scheduler.py --list
  Dry-run (default; nao chama LLM):      python scripts/run_scheduler.py
  Executar de fato (exige a env):        set LILO_ENABLE_SCHEDULER=1
                                         python scripts/run_scheduler.py --execute

Execucao real roda SEMPRE sob perfil 'cowork' (local-only, sem shell/python) e
exec_mode 'ask'; as saidas ficam em KVMemory (ns lilo_tasks) para revisao.
"""

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared import scheduler


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true",
                   help="lista as tarefas, seu schedule e se estao 'due'")
    p.add_argument("--execute", action="store_true",
                   help="executa de fato (senao DRY-RUN); exige LILO_ENABLE_SCHEDULER=1")
    p.add_argument("--max", type=int, default=5, help="teto de tarefas por corrida")
    args = p.parse_args()

    if args.list:
        tasks = scheduler.list_tasks()
        if not tasks:
            print("(nenhuma tarefa agendada encontrada; veja LILO_SCHEDULED_DIRS)")
            return 0
        for t in tasks:
            print("%-32s schedule=%-8s enabled=%-5s due=%s" % (
                t["name"][:32], t.get("schedule"), t.get("enabled"),
                scheduler.is_due(t)))
        return 0

    res = scheduler.run_due_tasks(dry_run=not args.execute, max_tasks=args.max)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if res.get("blocked"):
        print("\n[scheduler] BLOQUEADO: " + res.get("reason", ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
