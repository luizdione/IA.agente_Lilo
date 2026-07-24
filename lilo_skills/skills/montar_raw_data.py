"""Skill portada de ~/.claude/skills/montagem_resultados (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "montagem_resultados" / "scripts/montar_raw_data.py"


def montar_raw_data(args=None, env="datascience", timeout=300):
    """Executa scripts/montar_raw_data.py (skill montagem_resultados). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
