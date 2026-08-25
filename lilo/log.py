"""Logger do LILO — sempre em STDERR (stdout pertence a conversa do REPL;
heranca do shared/logger.py do legado, que reservava stdout p/ MCP) + arquivo
em <dados>/logs/lilo.log. Idempotente por nome."""
from __future__ import annotations

import logging
import sys

from lilo import config

_FMT = "%(asctime)s [LILO.%(name)s] %(levelname)s: %(message)s"


def get_logger(nome: str) -> logging.Logger:
    log = logging.getLogger("lilo." + nome)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    log.propagate = False

    con = logging.StreamHandler(sys.stderr)
    con.setFormatter(logging.Formatter(_FMT, datefmt="%H:%M:%S"))
    log.addHandler(con)

    try:
        pasta = config.dir_dados() / "logs"
        pasta.mkdir(parents=True, exist_ok=True)
        arq = logging.FileHandler(pasta / "lilo.log", encoding="utf-8")
        arq.setFormatter(logging.Formatter(_FMT))
        log.addHandler(arq)
    except OSError:
        pass  # sem disco p/ log de arquivo nao derruba o agente

    return log
