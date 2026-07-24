"""Skill portada de ~/.claude/skills/git_dione (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "git_dione" / "git_dione_sync.py"


def git_sync(args=None, env="datascience", timeout=300):
    """Executa git_dione_sync.py (skill git_dione). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
