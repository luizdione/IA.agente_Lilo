"""
shared/logger.py — Logger padronizado para todos os subagentes LILO.
Uso:
    from shared.logger import get_logger
    log = get_logger("MeuAgente")
    log.info("Iniciando...")
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Retorna logger configurado com handler stdout + arquivo rotativo.
    Idempotente: múltiplas chamadas com mesmo 'name' retornam o mesmo logger.
    """
    log = logging.getLogger(f"LILO.{name}")

    if log.handlers:
        return log  # já configurado

    log.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: stderr (não pode ser stdout — MCP usa stdin/stdout para JSON-RPC)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    # Handler: arquivo (lilo.log na raiz do projeto)
    try:
        fh = logging.FileHandler(LOG_DIR / "lilo.log", encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        pass  # sem acesso a disco → só stdout

    log.propagate = False
    return log
