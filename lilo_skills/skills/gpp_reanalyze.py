"""Skill portada de ~/.claude/skills/graphpad_prism (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "graphpad_prism" / "scripts/prism_reanalyze.py"


def gpp_reanalyze(args=None, env="datascience", timeout=300):
    """Executa scripts/prism_reanalyze.py (skill graphpad_prism). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
