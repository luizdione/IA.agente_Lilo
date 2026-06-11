"""
Orquestrador do Agente Autônomo
Implementa o loop de raciocínio: plan → act → observe → refine
"""

from typing import Dict, Any, List, Optional
import structlog
from enum import Enum
import asyncio

from app.core.config import settings
from app.services.llm_service import LLMService, ModelRole
from app.services.memory_service import MemoryService
from app.tools.file_operations import file_ops
from app.models.agent_state import AgentState, TaskStatus

logger = structlog.get_logger()


class AgentPhase(str, Enum):
    """Fases do loop de raciocínio"""
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFINE = "refine"
    COMPLETE = "complete"


class AgentOrchestrator:
    """
    Orquestrador principal do agente autônomo
    Implementa loop iterativo de raciocínio
    """

    def __init__(self):
        self.llm_service: Optional[LLMService] = None
        self.memory_service: Optional[MemoryService] = None
        self.current_state: Optional[AgentState] = None
        self.max_iterations = 10

    async def initialize(self):
        """Inicializa serviços"""
        logger.info("Inicializando orquestrador do agente")

        # Inicializar LLM service
        self.llm_service = LLMService()
        await self.llm_service.initialize()

        # Inicializar Memory service
        self.memory_service = MemoryService()
        await self.memory_service.initialize()

        logger.info("Orquestrador inicializado")

    async def shutdown(self):
        """Finaliza serviços"""
        logger.info("Finalizando orquestrador")

        if self.memory_service:
            await self.memory_service.shutdown()

    async def execute_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa uma tarefa usando loop de raciocínio iterativo

        Args:
            task: Descrição da tarefa
            context: Contexto adicional

        Returns:
            Resultado da execução
        """
        logger.info("Iniciando execução de tarefa", task=task)

        # Inicializar estado
        self.current_state = AgentState(
            task=task,
            context=context or {},
            phase=AgentPhase.PLAN,
            iteration=0
        )

        # Loop de raciocínio
        for iteration in range(self.max_iterations):
            self.current_state.iteration = iteration

            logger.info("Iteração do loop", iteration=iteration, phase=self.current_state.phase)

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

            # Evitar loop infinito
            if iteration >= self.max_iterations - 1:
                logger.warning("Limite de iterações atingido")
                self.current_state.status = TaskStatus.FAILED
                self.current_state.phase = AgentPhase.COMPLETE
                break

        # Salvar na memória de longo prazo
        await self._save_to_memory()

        return self._build_response()

    async def _phase_plan(self):
        """Fase 1: Planejamento"""
        logger.info("FASE: Planejamento")

        # Buscar contexto relevante da memória
        memory_context = await self.memory_service.search_relevant(
            self.current_state.task,
            limit=5
        )

        # Usar modelo planner
        prompt = self._build_planning_prompt(memory_context)
        plan = await self.llm_service.generate(
            prompt=prompt,
            role=ModelRole.PLANNER,
            temperature=0.2
        )

        self.current_state.plan = plan
        self.current_state.phase = AgentPhase.ACT

        logger.info("Plano gerado", plan=plan[:200])

    async def _phase_act(self):
        """Fase 2: Ação/Execução"""
        logger.info("FASE: Ação")

        # Usar modelo executor
        prompt = self._build_execution_prompt()
        actions = await self.llm_service.generate_with_tools(
            prompt=prompt,
            role=ModelRole.EXECUTOR,
            tools=self._get_available_tools()
        )

        self.current_state.actions = actions
        self.current_state.phase = AgentPhase.OBSERVE

        logger.info("Ações executadas", actions_count=len(actions))

    async def _phase_observe(self):
        """Fase 3: Observação"""
        logger.info("FASE: Observação")

        # Coletar resultados das ações
        observations = await self._collect_observations()

        self.current_state.observations = observations
        self.current_state.phase = AgentPhase.REFINE

        logger.info("Observações coletadas", observations_count=len(observations))

    async def _phase_refine(self):
        """Fase 4: Refinamento"""
        logger.info("FASE: Refinamento")

        # Usar modelo critic para avaliar
        prompt = self._build_refinement_prompt()
        evaluation = await self.llm_service.generate(
            prompt=prompt,
            role=ModelRole.CRITIC,
            temperature=0.1
        )

        # Decidir próxima fase
        if self._is_task_complete(evaluation):
            self.current_state.status = TaskStatus.COMPLETED
            self.current_state.phase = AgentPhase.COMPLETE
            logger.info("Tarefa completada com sucesso")
        else:
            # Refinar plano e continuar
            self.current_state.refinement = evaluation
            self.current_state.phase = AgentPhase.PLAN
            logger.info("Tarefa requer refinamento, reiniciando loop")

    async def _collect_observations(self) -> List[Dict[str, Any]]:
        """Coleta observações dos resultados das ações"""
        observations = []

        for action in self.current_state.actions:
            try:
                result = await self._execute_action(action)
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

        return observations

    async def _execute_action(self, action: Dict[str, Any]) -> Any:
        """Executa uma ação específica"""
        action_type = action.get("type")

        if action_type == "read_file":
            return await file_ops.read_file(action["path"])
        elif action_type == "write_file":
            return await file_ops.write_file(action["path"], action["content"])
        elif action_type == "create_file":
            return await file_ops.create_file(action["path"], action.get("content", ""))
        elif action_type == "delete_file":
            return await file_ops.delete_file(action["path"])
        elif action_type == "list_directory":
            return await file_ops.list_directory(action["path"])
        else:
            raise ValueError(f"Tipo de ação desconhecido: {action_type}")

    def _build_planning_prompt(self, memory_context: List[str]) -> str:
        """Constrói prompt para fase de planejamento"""
        context_str = "\n".join(memory_context) if memory_context else "Nenhum contexto anterior"

        return f"""Você é um assistente de planejamento estratégico.

Tarefa: {self.current_state.task}

Contexto relevante da memória:
{context_str}

Contexto adicional:
{self.current_state.context}

Crie um plano detalhado para executar esta tarefa. O plano deve:
1. Ser específico e acionável
2. Considerar o contexto fornecido
3. Incluir passos claros e sequenciais
4. Identificar recursos necessários

Plano:"""

    def _build_execution_prompt(self) -> str:
        """Constrói prompt para fase de execução"""
        return f"""Você é um executor especializado em código e operações de arquivo.

Tarefa: {self.current_state.task}

Plano:
{self.current_state.plan}

Execute o plano usando as ferramentas disponíveis. Para cada ação:
1. Use a ferramenta apropriada
2. Forneça todos os parâmetros necessários
3. Considere dependências entre ações

Ações:"""

    def _build_refinement_prompt(self) -> str:
        """Constrói prompt para fase de refinamento"""
        return f"""Você é um crítico rigoroso que avalia resultados.

Tarefa original: {self.current_state.task}

Plano: {self.current_state.plan}

Observações das ações executadas:
{self.current_state.observations}

Avalie:
1. A tarefa foi completada com sucesso?
2. Os resultados atendem aos requisitos?
3. Há erros ou problemas?
4. Refinamentos são necessários?

Forneça uma avaliação detalhada e recomendações:"""

    def _is_task_complete(self, evaluation: str) -> bool:
        """Determina se a tarefa está completa baseado na avaliação"""
        # Lógica simples - pode ser melhorada com parsing estruturado
        keywords_success = ["completa", "sucesso", "concluída", "finalizada"]
        keywords_failure = ["erro", "falha", "incompleta", "refinamento necessário"]

        eval_lower = evaluation.lower()

        has_success = any(kw in eval_lower for kw in keywords_success)
        has_failure = any(kw in eval_lower for kw in keywords_failure)

        return has_success and not has_failure

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Retorna lista de ferramentas disponíveis"""
        return [
            {
                "name": "read_file",
                "description": "Lê conteúdo de um arquivo",
                "parameters": {"path": "string"}
            },
            {
                "name": "write_file",
                "description": "Escreve conteúdo em um arquivo",
                "parameters": {"path": "string", "content": "string"}
            },
            {
                "name": "create_file",
                "description": "Cria um novo arquivo",
                "parameters": {"path": "string", "content": "string (opcional)"}
            },
            {
                "name": "delete_file",
                "description": "Deleta um arquivo",
                "parameters": {"path": "string"}
            },
            {
                "name": "list_directory",
                "description": "Lista conteúdo de um diretório",
                "parameters": {"path": "string", "recursive": "boolean (opcional)"}
            }
        ]

    async def _save_to_memory(self):
        """Salva execução na memória de longo prazo"""
        memory_entry = {
            "task": self.current_state.task,
            "plan": self.current_state.plan,
            "status": self.current_state.status,
            "iterations": self.current_state.iteration,
            "result": self._build_response()
        }

        await self.memory_service.add_memory(
            content=str(memory_entry),
            metadata=memory_entry
        )

    def _build_response(self) -> Dict[str, Any]:
        """Constrói resposta final"""
        return {
            "task": self.current_state.task,
            "status": self.current_state.status,
            "plan": self.current_state.plan,
            "actions": self.current_state.actions,
            "observations": self.current_state.observations,
            "refinement": self.current_state.refinement,
            "iterations": self.current_state.iteration
        }
