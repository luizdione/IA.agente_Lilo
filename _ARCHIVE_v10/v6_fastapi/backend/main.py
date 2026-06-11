"""
Backend FastAPI - Orquestração do Agente Autônomo LILO v6.0
Arquitetura: Serviço backend otimizado com lazy loading de modelos
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from prometheus_client import make_asgi_app

from app.api.routes import agent, files, memory, health, subagents
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.agent_orchestrator_optimized import OptimizedAgentOrchestrator
from app.services.model_manager import ModelManager

# Setup logging estruturado
setup_logging()
logger = structlog.get_logger()

# Instâncias globais
orchestrator: OptimizedAgentOrchestrator = None
model_manager: ModelManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    global orchestrator, model_manager

    logger.info("Iniciando backend LILO v6.0", version=settings.VERSION)

    # Inicializar Model Manager primeiro (com lazy loading)
    model_manager = ModelManager()
    await model_manager.initialize()
    logger.info("Model Manager inicializado (lazy loading ativado)")

    # Inicializar orquestrador otimizado
    orchestrator = OptimizedAgentOrchestrator()
    await orchestrator.initialize()
    logger.info("Orquestrador otimizado inicializado")

    # Tornar model_manager acessível globalmente para sub-agentes
    import app.services.model_manager as mm
    mm.model_manager = model_manager

    logger.info("Backend LILO v6.0 inicializado com sucesso")

    yield

    # Shutdown
    logger.info("Finalizando backend LILO v6.0")
    if orchestrator:
        await orchestrator.shutdown()
    if model_manager:
        await model_manager.shutdown()


# Criar aplicação FastAPI
app = FastAPI(
    title="LILO Agent API v6.0",
    description="API de orquestração do agente autônomo LILO com lazy loading e sub-agentes",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Rotas
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(subagents.router, prefix="/subagents", tags=["Sub-Agents"])


def get_orchestrator() -> OptimizedAgentOrchestrator:
    """Dependency injection do orquestrador"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orquestrador não inicializado")
    return orchestrator


def get_model_manager() -> ModelManager:
    """Dependency injection do model manager"""
    if model_manager is None:
        raise HTTPException(status_code=503, detail="Model Manager não inicializado")
    return model_manager


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "service": "LILO Agent API",
        "version": settings.VERSION,
        "status": "running",
        "features": [
            "Lazy Loading de Modelos",
            "Sub-Agentes (PDF Scholar, SQL Analysis)",
            "RAG com ChromaDB",
            "File Operations com Permissões",
            "Loop de Raciocínio Otimizado"
        ],
        "docs": "/docs"
    }


@app.get("/info")
async def system_info():
    """Informações do sistema"""
    info = {
        "version": settings.VERSION,
        "ollama_host": settings.OLLAMA_HOST,
        "debug": settings.DEBUG,
    }

    if model_manager:
        info["models"] = {
            "loaded": list(model_manager.loaded_models.keys()),
            "current_large": model_manager.current_large_model,
            "cache_size": len(model_manager.response_cache)
        }

    if orchestrator and orchestrator.current_state:
        info["agent"] = {
            "active": True,
            "task": orchestrator.current_state.task[:100],
            "phase": orchestrator.current_state.phase,
            "iteration": orchestrator.current_state.iteration
        }
    else:
        info["agent"] = {"active": False}

    return info


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("🤖 LILO Agent API v6.0")
    print("=" * 70)
    print("\n✨ Recursos:")
    print("  • Lazy Loading de Modelos (máx 1 pesado por vez)")
    print("  • Sub-Agentes: PDF Scholar, SQL Analysis")
    print("  • RAG com ChromaDB")
    print("  • Loop Otimizado: route → plan → act → observe → refine")
    print("\n🔗 Endpoints:")
    print("  • Docs: http://localhost:8000/docs")
    print("  • Info: http://localhost:8000/info")
    print("  • Health: http://localhost:8000/health/")
    print("\n" + "=" * 70 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
