#!/usr/bin/env python3
"""
LILO Backend - Aplicacao FastAPI Principal
"""

from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import routers
from app.api.routes import agent, files, memory, health, subagents

# Criar app FastAPI
app = FastAPI(
    title="LILO Agent API",
    description="API Backend para LILO - Sistema Autonomo de IA",
    version="6.0.0"
)

# CORS middleware para permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(subagents.router, prefix="/subagents", tags=["Subagents"])


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz"""
    return {
        "name": "LILO Agent API",
        "version": "6.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "health": "/health/"
    }


@app.on_event("startup")
async def startup_event():
    """Evento de inicializacao"""
    print("=" * 70)
    print("LILO Agent Backend - Iniciando")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("Documentacao: http://localhost:8000/docs")
    print("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de encerramento"""
    print("\nLILO Agent Backend - Encerrando")




@app.get("/health/", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "6.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
