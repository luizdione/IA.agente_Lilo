"""Skill portada de ~/.claude/skills/perfil_dados (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "perfil_dados" / "scripts/perfil.py"


def perfil_dados(args=None, env="datascience", timeout=300):
    """Executa scripts/perfil.py (skill perfil_dados). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
