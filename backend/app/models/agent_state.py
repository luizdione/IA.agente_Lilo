"""
Modelos de estado do agente
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """Status da tarefa"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(BaseModel):
    """Estado do agente durante execução"""
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    phase: str
    iteration: int = 0
    status: TaskStatus = TaskStatus.IN_PROGRESS

    # Outputs de cada fase
    plan: Optional[str] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    refinement: Optional[str] = None

    # Metadados
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
