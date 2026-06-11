"""
Model Manager - Gerenciamento otimizado de modelos com Lazy Loading
Carrega modelos SOB DEMANDA para não sobrecarregar memória/VRAM
"""

from typing import Dict, Any, Optional, List
import structlog
import httpx
from enum import Enum
from datetime import datetime, timedelta
import asyncio

from app.core.config import settings

logger = structlog.get_logger()


class ModelRole(str, Enum):
    """Papéis dos modelos - apenas os essenciais"""
    ROUTER = "router"          # Roteamento de tarefas (leve)
    PLANNER = "planner"        # Planejamento (médio)
    EXECUTOR = "executor"      # Execução código (pesado)
    CHAT = "chat"              # Conversação (leve)
    ANALYSIS = "analysis"      # Análise SQL/dados (médio)
    SCHOLAR = "scholar"        # Documentos científicos (pesado)


class ModelManager:
    """
    Gerenciador de modelos com lazy loading e descarregamento automático
    Garante que apenas 1 modelo pesado está carregado por vez
    """

    # Configuração de modelos (do menor para maior)
    MODEL_CONFIG = {
        ModelRole.ROUTER: {
            "model": "qwen2.5-coder:7b",  # Leve e rápido para roteamento
            "size": "small",
            "max_tokens": 2048,
            "temperature": 0.1,
            "priority": 1,  # Sempre disponível
        },
        ModelRole.CHAT: {
            "model": "llama3.1:8b-instruct-q8_0",
            "size": "medium",
            "max_tokens": 4096,
            "temperature": 0.7,
            "priority": 2,
        },
        ModelRole.PLANNER: {
            "model": "phi3:14b-medium-128k-instruct-q4_K_M",
            "size": "medium",
            "max_tokens": 8192,
            "temperature": 0.2,
            "priority": 3,
        },
        ModelRole.ANALYSIS: {
            "model": "deepseek-coder-v2:16b",
            "size": "large",
            "max_tokens": 8192,
            "temperature": 0.2,
            "priority": 4,
        },
        ModelRole.EXECUTOR: {
            "model": "qwen2.5-coder:14b",
            "size": "large",
            "max_tokens": 8192,
            "temperature": 0.2,
            "priority": 4,
        },
        ModelRole.SCHOLAR: {
            "model": "mistral-large-3:675b-cloud",  # Se disponível, senão usa executor
            "fallback": "qwen2.5-coder:14b",
            "size": "xlarge",
            "max_tokens": 16384,
            "temperature": 0.3,
            "priority": 5,
        },
    }

    def __init__(self):
        self.ollama_host = settings.OLLAMA_HOST
        self.client: Optional[httpx.AsyncClient] = None

        # Controle de modelos carregados
        self.loaded_models: Dict[ModelRole, Dict[str, Any]] = {}
        self.last_used: Dict[ModelRole, datetime] = {}

        # Apenas 1 modelo pesado por vez
        self.max_large_models = 1
        self.current_large_model: Optional[ModelRole] = None

        # Cache de respostas recentes
        self.response_cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=5)

    async def initialize(self):
        """Inicializa cliente e pre-carrega modelo leve de roteamento"""
        self.client = httpx.AsyncClient(base_url=self.ollama_host, timeout=300.0)
        logger.info("Model Manager inicializado", host=self.ollama_host)

        # Pre-carregar apenas o roteador (leve)
        await self._ensure_model_loaded(ModelRole.ROUTER)

    async def _ensure_model_loaded(self, role: ModelRole) -> str:
        """
        Garante que modelo está carregado, fazendo lazy loading se necessário

        Returns:
            Nome do modelo carregado
        """
        config = self.MODEL_CONFIG[role]
        model_name = config["model"]
        model_size = config["size"]

        # Se já está carregado, apenas atualiza timestamp
        if role in self.loaded_models:
            self.last_used[role] = datetime.utcnow()
            logger.debug("Modelo já carregado", role=role.value, model=model_name)
            return model_name

        # Se é modelo pesado, descarregar outro modelo pesado primeiro
        if model_size in ["large", "xlarge"]:
            await self._unload_large_models(except_role=role)

        # Verificar se modelo existe
        available = await self._get_available_models()

        if model_name not in available:
            # Tentar fallback
            fallback = config.get("fallback")
            if fallback and fallback in available:
                logger.warning("Modelo não encontrado, usando fallback",
                             original=model_name, fallback=fallback)
                model_name = fallback
            else:
                raise ValueError(f"Modelo {model_name} não disponível e sem fallback")

        # Marcar como carregado
        self.loaded_models[role] = {
            "model": model_name,
            "size": model_size,
            "loaded_at": datetime.utcnow()
        }
        self.last_used[role] = datetime.utcnow()

        if model_size in ["large", "xlarge"]:
            self.current_large_model = role

        logger.info("Modelo carregado", role=role.value, model=model_name, size=model_size)
        return model_name

    async def _unload_large_models(self, except_role: Optional[ModelRole] = None):
        """Descarrega modelos pesados da memória"""
        to_unload = []

        for role, info in list(self.loaded_models.items()):
            if role == except_role:
                continue

            if info["size"] in ["large", "xlarge"]:
                to_unload.append(role)

        for role in to_unload:
            model_name = self.loaded_models[role]["model"]

            # Chamar API do Ollama para descarregar (se suportado)
            # Por enquanto, apenas remover do tracking
            del self.loaded_models[role]
            if role in self.last_used:
                del self.last_used[role]

            logger.info("Modelo descarregado", role=role.value, model=model_name)

        self.current_large_model = None

    async def _get_available_models(self) -> List[str]:
        """Obtém lista de modelos disponíveis no Ollama"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            logger.error("Erro ao listar modelos", error=str(e))
            return []

    async def generate(
        self,
        prompt: str,
        role: ModelRole = ModelRole.CHAT,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gera resposta usando modelo apropriado

        Args:
            prompt: Prompt de entrada
            role: Papel do modelo
            system_prompt: System prompt customizado
            temperature: Temperatura (override)

        Returns:
            Resposta gerada
        """
        # Verificar cache
        cache_key = f"{role.value}:{hash(prompt)}"
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            if datetime.utcnow() - cached["timestamp"] < self.cache_ttl:
                logger.debug("Resposta do cache", role=role.value)
                return cached["response"]

        # Garantir que modelo está carregado
        model_name = await self._ensure_model_loaded(role)
        config = self.MODEL_CONFIG[role]

        # Preparar payload
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or config["temperature"],
                "num_ctx": config["max_tokens"],
                "num_predict": -1,  # Sem limite (usar max_tokens)
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        logger.info("Gerando resposta", role=role.value, model=model_name)

        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            generated = result.get("response", "")

            # Armazenar em cache
            self.response_cache[cache_key] = {
                "response": generated,
                "timestamp": datetime.utcnow()
            }

            # Limpar cache antigo (max 100 entradas)
            if len(self.response_cache) > 100:
                oldest = min(self.response_cache.items(),
                           key=lambda x: x[1]["timestamp"])
                del self.response_cache[oldest[0]]

            logger.info("Resposta gerada", role=role.value, length=len(generated))
            return generated

        except Exception as e:
            logger.error("Erro ao gerar resposta", role=role.value, error=str(e))
            raise

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        role: ModelRole = ModelRole.EXECUTOR
    ) -> List[Dict[str, Any]]:
        """
        Gera resposta com tool calling

        Returns:
            Lista de tool calls
        """
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in tools
        ])

        enhanced_prompt = f"""{prompt}

Ferramentas disponíveis:
{tools_desc}

Responda APENAS com um JSON array de tool calls no formato:
[
  {{"tool": "nome_ferramenta", "params": {{"param1": "valor1"}}}},
  ...
]

Tool calls:"""

        response = await self.generate(enhanced_prompt, role=role, temperature=0.1)

        # Parse JSON
        try:
            import json
            import re

            # Extrair JSON da resposta
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                tool_calls = json.loads(match.group(0))
                return tool_calls
            else:
                logger.warning("Nenhum tool call encontrado na resposta")
                return []

        except Exception as e:
            logger.error("Erro ao parsear tool calls", error=str(e))
            return []

    async def shutdown(self):
        """Finaliza e descarrega todos os modelos"""
        await self._unload_large_models()

        if self.client:
            await self.client.aclose()

        logger.info("Model Manager finalizado")


# Instância global (será inicializada no startup)
model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Obtém instância global do model manager"""
    if model_manager is None:
        raise RuntimeError("Model Manager não inicializado")
    return model_manager
