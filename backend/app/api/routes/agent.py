"""
Rotas da API - Controle do Agente
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.services.agent_orchestrator import AgentOrchestrator
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Dependência para obter orquestrador (será injetada no main.py)
_orchestrator: Optional[AgentOrchestrator] = None


def set_orchestrator(orch: AgentOrchestrator):
    global _orchestrator
    _orchestrator = orch


def get_orchestrator() -> AgentOrchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orquestrador não disponível")
    return _orchestrator


class TaskRequest(BaseModel):
    """Request para executar tarefa"""
    task: str
    context: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Response de execução de tarefa"""
    task: str
    status: str
    result: Dict[str, Any]


@router.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    Executa uma tarefa usando o agente autônomo

    - **task**: Descrição da tarefa a executar
    - **context**: Contexto adicional (opcional)
    """
    logger.info("API: Recebida requisição de tarefa", task=request.task)

    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.execute_task(request.task, request.context)

        return TaskResponse(
            task=request.task,
            status=result.get("status", "unknown"),
            result=result
        )

    except Exception as e:
        logger.error("Erro ao executar tarefa", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Obtém status do agente"""
    orchestrator = get_orchestrator()

    if orchestrator.current_state:
        return {
            "active": True,
            "task": orchestrator.current_state.task,
            "phase": orchestrator.current_state.phase,
            "iteration": orchestrator.current_state.iteration,
            "status": orchestrator.current_state.status
        }
    else:
        return {
            "active": False,
            "message": "Nenhuma tarefa em execução"
        }
