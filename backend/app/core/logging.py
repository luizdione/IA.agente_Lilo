"""
Sistema de logging estruturado
"""

import structlog
import logging
import sys
from pathlib import Path


def setup_logging():
    """Configura logging estruturado com structlog"""

    # Criar diretório de logs (ignora se não tiver permissão fora do Docker)
    try:
        log_dir = Path("/app/logs")
        if log_dir.parent.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False
    )
