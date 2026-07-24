"""Skill portada de ~/.claude/skills/biblioteca_ref (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "biblioteca_ref" / "scripts/bibref.py"


def bibref(args=None, env="datascience", timeout=300):
    """Executa scripts/bibref.py (skill biblioteca_ref). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
