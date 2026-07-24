"""Skill portada de ~/.claude/skills/derobotizar_artigo (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "check_integrity" / "assets/check_integrity.py"


def check_integrity(args=None, env="datascience", timeout=300):
    """Executa assets/check_integrity.py (skill derobotizar_artigo). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
