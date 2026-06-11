"""
Serviço de LLM - Interface com Ollama
Gerencia múltiplos modelos especializados
"""

from typing import Dict, Any, List, Optional
import structlog
import httpx
from enum import Enum

from app.core.config import settings

logger = structlog.get_logger()


class ModelRole(str, Enum):
    """Papéis dos modelos"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    CHAT = "chat"


class LLMService:
    """Serviço de gerenciamento de LLMs"""

    def __init__(self):
        self.ollama_host = settings.OLLAMA_HOST
        self.models = {
            ModelRole.PLANNER: settings.OLLAMA_MODEL_PLANNER,
            ModelRole.EXECUTOR: settings.OLLAMA_MODEL_EXECUTOR,
            ModelRole.CRITIC: settings.OLLAMA_MODEL_CRITIC,
            ModelRole.CHAT: settings.OLLAMA_MODEL_CHAT,
        }
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Inicializa cliente HTTP"""
        self.client = httpx.AsyncClient(base_url=self.ollama_host, timeout=120.0)
        logger.info("LLM Service inicializado", host=self.ollama_host)

        # Verificar modelos disponíveis
        await self._verify_models()

    async def _verify_models(self):
        """Verifica se modelos estão disponíveis"""
        try:
            response = await self.client.get("/api/tags")
            available = {m["name"] for m in response.json().get("models", [])}

            for role, model in self.models.items():
                if model not in available:
                    logger.warning("Modelo não encontrado", role=role, model=model)
                else:
                    logger.info("Modelo disponível", role=role, model=model)

        except Exception as e:
            logger.error("Erro ao verificar modelos", error=str(e))

    async def generate(
        self,
        prompt: str,
        role: ModelRole = ModelRole.CHAT,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Gera resposta usando modelo apropriado

        Args:
            prompt: Prompt de entrada
            role: Papel do modelo a usar
            temperature: Temperatura de geração
            max_tokens: Máximo de tokens (opcional)

        Returns:
            Resposta gerada
        """
        model = self.models[role]

        logger.info("Gerando resposta", model=model, role=role)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "")

            logger.info("Resposta gerada", model=model, length=len(generated_text))
            return generated_text

        except Exception as e:
            logger.error("Erro ao gerar resposta", model=model, error=str(e))
            raise

    async def generate_with_tools(
        self,
        prompt: str,
        role: ModelRole = ModelRole.EXECUTOR,
        tools: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Gera resposta com tool calling

        Args:
            prompt: Prompt de entrada
            role: Papel do modelo
            tools: Lista de ferramentas disponíveis

        Returns:
            Lista de ações (tool calls)
        """
        # Construir prompt com ferramentas
        tools_description = self._format_tools(tools or [])

        enhanced_prompt = f"""{prompt}

Ferramentas disponíveis:
{tools_description}

Forneça as ações necessárias no formato JSON:
[
  {{"type": "nome_ferramenta", "parametro1": "valor1", ...}},
  ...
]

Ações:"""

        response = await self.generate(enhanced_prompt, role=role, temperature=0.2)

        # Parse de ações (simplificado - em produção usar parser robusto)
        try:
            import json
            # Tentar extrair JSON da resposta
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                actions = json.loads(json_str)
                return actions
            else:
                logger.warning("Nenhuma ação JSON encontrada na resposta")
                return []
        except Exception as e:
            logger.error("Erro ao parsear ações", error=str(e))
            return []

    def _format_tools(self, tools: List[Dict[str, Any]]) -> str:
        """Formata descrição de ferramentas"""
        lines = []
        for tool in tools:
            params = ", ".join(f"{k}: {v}" for k, v in tool.get("parameters", {}).items())
            lines.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(lines)

    async def embed(self, text: str) -> List[float]:
        """
        Gera embedding de texto

        Args:
            text: Texto para embedar

        Returns:
            Vetor de embedding
        """
        model = settings.OLLAMA_MODEL_EMBEDDINGS

        payload = {
            "model": model,
            "prompt": text
        }

        try:
            response = await self.client.post("/api/embeddings", json=payload)
            response.raise_for_status()

            result = response.json()
            embedding = result.get("embedding", [])

            logger.debug("Embedding gerado", model=model, dim=len(embedding))
            return embedding

        except Exception as e:
            logger.error("Erro ao gerar embedding", error=str(e))
            raise
