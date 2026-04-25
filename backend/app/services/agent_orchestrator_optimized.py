"""
Orquestrador Otimizado - Lazy Loading de Modelos
Carrega modelos apenas quando necessário, 1 por vez
"""

from typing import Dict, Any, List, Optional
import structlog
from enum import Enum
import asyncio

from app.core.config import settings
from app.services.model_manager import ModelManager, ModelRole, get_model_manager
from app.services.memory_service import MemoryService
from app.tools.file_operations import file_ops
from app.models.agent_state import AgentState, TaskStatus

logger = structlog.get_logger()


class AgentPhase(str, Enum):
    """Fases do loop de raciocínio"""
    ROUTE = "route"        # Roteamento de tarefa
    PLAN = "plan"          # Planejamento
    ACT = "act"            # Ação
    OBSERVE = "observe"    # Observação
    REFINE = "refine"      # Refinamento
    COMPLETE = "complete"  # Completo


class OptimizedAgentOrchestrator:
    """
    Orquestrador otimizado com lazy loading de modelos
    """

    def __init__(self):
        self.model_manager: Optional[ModelManager] = None
        self.memory_service: Optional[MemoryService] = None
        self.current_state: Optional[AgentState] = None
        self.max_iterations = 5  # Reduzido para performance

    async def initialize(self):
        """Inicializa serviços"""
        logger.info("Inicializando orquestrador otimizado")

        # Inicializar Model Manager (pre-carrega apenas roteador)
        self.model_manager = ModelManager()
        await self.model_manager.initialize()

        # Inicializar Memory service
        self.memory_service = MemoryService()
        await self.memory_service.initialize()

        logger.info("Orquestrador otimizado inicializado")

    async def shutdown(self):
        """Finaliza serviços"""
        logger.info("Finalizando orquestrador")

        if self.model_manager:
            await self.model_manager.shutdown()

        if self.memory_service:
            await self.memory_service.shutdown()

    async def execute_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executa tarefa com loop otimizado

        Fluxo:
        1. ROUTE: Determina tipo de tarefa (modelo leve)
        2. PLAN: Cria plano (modelo médio)
        3. ACT: Executa ações (modelo pesado se necessário)
        4. OBSERVE: Coleta resultados
        5. REFINE: Avalia e decide (modelo médio)
        """
        logger.info("Executando tarefa", task=task[:100])

        # Inicializar estado
        self.current_state = AgentState(
            task=task,
            context=context or {},
            phase=AgentPhase.ROUTE,
            iteration=0
        )

        # FASE 0: Roteamento (sempre executado)
        await self._phase_route()

        # Loop principal
        for iteration in range(self.max_iterations):
            self.current_state.iteration = iteration

            logger.info("Iteração do loop",
                       iteration=iteration,
                       phase=self.current_state.phase)

            # Executar fase atual
            if self.current_state.phase == AgentPhase.PLAN:
                await self._phase_plan()
            elif self.current_state.phase == AgentPhase.ACT:
                await self._phase_act()
            elif self.current_state.phase == AgentPhase.OBSERVE:
                await self._phase_observe()
            elif self.current_state.phase == AgentPhase.REFINE:
                await self._phase_refine()
            elif self.current_state.phase == AgentPhase.COMPLETE:
                break

            if iteration >= self.max_iterations - 1:
                logger.warning("Limite de iterações atingido")
                self.current_state.status = TaskStatus.COMPLETED
                self.current_state.phase = AgentPhase.COMPLETE
                break

        # Salvar na memória
        await self._save_to_memory()

        return self._build_response()

    async def _phase_route(self):
        """Fase 0: Roteamento de tarefa (modelo leve)"""
        logger.info("FASE: Roteamento")

        prompt = f"""Analise a seguinte tarefa e determine o tipo:

Tarefa: {self.current_state.task}

Tipos possíveis:
- code: Programação, refatoração, análise de código
- chat: Conversação, perguntas gerais
- analysis: Análise de dados, SQL, estatística
- scholar: Documentos científicos, PDFs, pesquisa
- file_ops: Operações de arquivo (ler, escrever, listar)

Responda APENAS com o tipo (uma palavra):"""

        task_type = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.ROUTER
        )

        task_type = task_type.strip().lower()
        self.current_state.context["task_type"] = task_type

        logger.info("Tarefa roteada", task_type=task_type)

        # Pular para fase apropriada
        if task_type in ["chat"]:
            # Chat direto, sem planejamento
            self.current_state.phase = AgentPhase.COMPLETE
            self.current_state.plan = await self.model_manager.generate(
                prompt=self.current_state.task,
                role=ModelRole.CHAT
            )
        else:
            # Tarefas complexas: planejar
            self.current_state.phase = AgentPhase.PLAN

    async def _phase_plan(self):
        """Fase 1: Planejamento (modelo médio)"""
        logger.info("FASE: Planejamento")

        # Buscar contexto da memória
        memory_context = await self.memory_service.search_relevant(
            self.current_state.task,
            limit=3
        )

        context_str = "\n".join(memory_context) if memory_context else "Sem contexto anterior"

        prompt = f"""Você é um assistente de planejamento estratégico.

Tarefa: {self.current_state.task}

Tipo de tarefa: {self.current_state.context.get('task_type', 'unknown')}

Contexto da memória:
{context_str}

Crie um plano de ação CONCISO (máximo 5 passos) para executar esta tarefa.
Liste apenas os passos essenciais, sem explicações longas.

Plano:"""

        plan = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.PLANNER
        )

        self.current_state.plan = plan
        self.current_state.phase = AgentPhase.ACT

        logger.info("Plano gerado", plan_length=len(plan))

    async def _phase_act(self):
        """Fase 2: Ação (modelo pesado se necessário)"""
        logger.info("FASE: Ação")

        task_type = self.current_state.context.get("task_type", "code")

        # Escolher modelo apropriado
        if task_type == "analysis":
            role = ModelRole.ANALYSIS
        elif task_type == "scholar":
            role = ModelRole.SCHOLAR
        else:
            role = ModelRole.EXECUTOR

        # Listar ferramentas disponíveis
        tools = self._get_available_tools()

        prompt = f"""Execute o seguinte plano usando as ferramentas disponíveis.

Plano:
{self.current_state.plan}

Tarefa original: {self.current_state.task}

Gere as ações necessárias."""

        actions = await self.model_manager.generate_with_tools(
            prompt=prompt,
            tools=tools,
            role=role
        )

        self.current_state.actions = actions
        self.current_state.phase = AgentPhase.OBSERVE

        logger.info("Ações geradas", count=len(actions))

    async def _phase_observe(self):
        """Fase 3: Observação"""
        logger.info("FASE: Observação")

        observations = []

        for action in self.current_state.actions:
            try:
                result = await self._execute_tool(action)
                observations.append({
                    "action": action,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                logger.error("Erro ao executar ação", action=action, error=str(e))
                observations.append({
                    "action": action,
                    "error": str(e),
                    "success": False
                })

        self.current_state.observations = observations
        self.current_state.phase = AgentPhase.REFINE

        logger.info("Observações coletadas", count=len(observations))

    async def _phase_refine(self):
        """Fase 4: Refinamento"""
        logger.info("FASE: Refinamento")

        # Avaliar se tarefa está completa
        prompt = f"""Avalie se a tarefa foi completada com sucesso.

Tarefa: {self.current_state.task}

Plano: {self.current_state.plan}

Resultados:
{self._format_observations()}

Responda APENAS:
- "COMPLETO" se a tarefa foi executada com sucesso
- "REFINAR" se precisa ajustes ou mais iterações
- "FALHA" se houve erro crítico

Avaliação:"""

        evaluation = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.PLANNER,
            temperature=0.1
        )

        evaluation = evaluation.strip().upper()

        if "COMPLETO" in evaluation:
            self.current_state.status = TaskStatus.COMPLETED
            self.current_state.phase = AgentPhase.COMPLETE
            logger.info("Tarefa completada com sucesso")
        elif "FALHA" in evaluation:
            self.current_state.status = TaskStatus.FAILED
            self.current_state.phase = AgentPhase.COMPLETE
            logger.warning("Tarefa falhou")
        else:
            # Refinar: voltar para planejamento
            self.current_state.refinement = evaluation
            self.current_state.phase = AgentPhase.PLAN
            logger.info("Tarefa requer refinamento")

    def _format_observations(self) -> str:
        """Formata observações para prompt"""
        lines = []
        for obs in self.current_state.observations:
            if obs["success"]:
                lines.append(f"✓ {obs['action']['tool']}: {str(obs['result'])[:100]}")
            else:
                lines.append(f"✗ {obs['action']['tool']}: {obs['error']}")
        return "\n".join(lines) if lines else "Nenhuma observação"

    async def _execute_tool(self, action: Dict[str, Any]) -> Any:
        """Executa uma ferramenta"""
        tool = action.get("tool")
        params = action.get("params", {})

        if tool == "read_file":
            return await file_ops.read_file(params["path"])
        elif tool == "write_file":
            return await file_ops.write_file(params["path"], params["content"])
        elif tool == "list_directory":
            return await file_ops.list_directory(params["path"])
        elif tool == "create_file":
            return await file_ops.create_file(params["path"], params.get("content", ""))
        elif tool == "delete_file":
            return await file_ops.delete_file(params["path"])
        else:
            raise ValueError(f"Ferramenta desconhecida: {tool}")

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Retorna ferramentas disponíveis"""
        return [
            {
                "name": "read_file",
                "description": "Lê arquivo",
                "params": {"path": "string"}
            },
            {
                "name": "write_file",
                "description": "Escreve arquivo",
                "params": {"path": "string", "content": "string"}
            },
            {
                "name": "list_directory",
                "description": "Lista diretório",
                "params": {"path": "string"}
            },
            {
                "name": "create_file",
                "description": "Cria arquivo",
                "params": {"path": "string", "content": "string"}
            },
            {
                "name": "delete_file",
                "description": "Deleta arquivo",
                "params": {"path": "string"}
            },
        ]

    async def _save_to_memory(self):
        """Salva execução na memória"""
        memory_entry = {
            "task": self.current_state.task,
            "task_type": self.current_state.context.get("task_type"),
            "plan": self.current_state.plan,
            "status": self.current_state.status,
            "iterations": self.current_state.iteration
        }

        await self.memory_service.add_memory(
            content=str(memory_entry),
            metadata=memory_entry
        )

    def _build_response(self) -> Dict[str, Any]:
        """Constrói resposta final"""
        return {
            "task": self.current_state.task,
            "task_type": self.current_state.context.get("task_type"),
            "status": self.current_state.status,
            "plan": self.current_state.plan,
            "actions": self.current_state.actions,
            "observations": self.current_state.observations,
            "iterations": self.current_state.iteration
        }
