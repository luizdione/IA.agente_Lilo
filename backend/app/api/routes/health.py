"""
Rotas da API - Health Check
"""

from fastapi import APIRouter
from datetime import datetime
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LILO Backend"
    }


@router.get("/ready")
async def readiness():
    """Readiness check para Kubernetes"""
    # Aqui podem ser adicionadas verificações de dependências
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness():
    """Liveness check para Kubernetes"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
