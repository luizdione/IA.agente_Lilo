"""
agents/gateway/agent.py — Adaptador LILO para o Gateway de LLMs.

Envolve o LiteLLM proxy (config/litellm_config.yaml) com interface BaseAgent,
servindo como fallback do orquestrador e roteador de modelos.

Movido em 2026-05-06 (arch-v10) de llm-gateway/agent.py para agents/gateway/agent.py
para uniformizar com os demais subagentes.
"""

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.utils import load_env, sanitize_query, truncate

load_env()


class GatewayAgent(BaseAgent):
    """
    Subagente Gateway de LLMs.

    Responsável por:
    - Servir como fallback quando nenhum subagente especializado é acionado
    - Roteamento entre modelos (llama3, codellama, claude, etc.)
    - Health check de todos os backends
    - Exposição do LiteLLM Proxy em localhost:4000
    """

    name = "gateway"
    description = (
        "Gateway central de LLMs: roteia para o modelo mais adequado "
        "(Ollama local, LiteLLM proxy, Claude API). Fallback geral do LILO."
    )

    # Sem keywords específicas — é o fallback quando nenhum outro agente match
    KEYWORDS: list[str] = []

    # V9 (2026-05-22): roteamento cost-aware no Villa_Lobos.
    # Chat geral/definições rápidas; local por padrão, mas é o ponto onde
    # a política de servidor pode optar por nuvem (allow_cloud).
    cost_tier = "ollama"
    local_only = True
    latency_class = "fast"

    def __init__(self):
        super().__init__()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    # ── Interface BaseAgent ──────────────────────────────────────────────────

    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        """
        Processa qualquer query como chat geral do LILO.

        context keys:
            model      — modelo específico a usar (opcional)
            mode       — "chat" | "code" | "bioinfo" | "sql" (default: "chat")
            temperature — float (default 0.3)
        """
        query  = sanitize_query(query)
        mode   = context.get("mode", "chat")
        model  = context.get("model", None)
        temp   = float(context.get("temperature", 0.3))

        self.log.info(f"Gateway query: {truncate(query, 80)} | mode={mode}")

        system_prompts = {
            "chat": (
                "Você é o LILO, um assistente de IA pessoal especializado em ciência de dados, "
                "bioinformática e automação de análises para pesquisadores. "
                "Responda de forma clara e prática. Português brasileiro."
            ),
            "code": (
                "Você é o LILO Code, especialista em Python, R, SQL e bioinformática computacional. "
                "Forneça código limpo, comentado e com exemplos de uso. Português brasileiro."
            ),
            "bioinfo": (
                "Você é o LILO Bio, especialista em genômica, proteômica, docking molecular, "
                "análise de sequências, pipelines NGS e visualização de dados biológicos. "
                "Soluções práticas e cientificamente fundamentadas. Português brasileiro."
            ),
            "sql": (
                "Você é o LILO SQL, especialista em bancos de dados e análise estatística "
                "para dados biológicos. Queries otimizadas e interpretação estatística. Português."
            ),
        }

        # Roteamento multi-modelo por modo (se não foi especificado explicitamente)
        from shared.llm_client import MODELS
        mode_model_map = {
            "chat":    MODELS.get("chat"),     # llama3.1:8b-instruct-q8_0
            "code":    MODELS.get("code"),     # qwen2.5-coder:14b
            "bioinfo": MODELS.get("plan"),     # phi3:14b-medium-128k-instruct-q4_K_M
            "sql":     MODELS.get("autocomplete"),  # qwen2.5-coder:7b-instruct
        }
        if model is None:
            model = mode_model_map.get(mode, MODELS.get("chat"))
            self.log.info(f"Modelo selecionado para modo '{mode}': {model}")

        # V15 FASE 0/1/2: consome ctx['system_hint'] (antes IGNORADO -> canal
        # morto), injeta honestidade/seguranca e o eixo de estilo. Tudo via
        # compose_system (respeita o kill-switch LILO_PROMPT_BLOCKS).
        from shared.prompt_blocks import compose_system
        try:
            from shared.response_style import get_style_block
            _style = get_style_block(context.get("response_style"))
        except Exception:
            _style = ""
        # V15.1: SECURITY_BLOCK DESLIGADO (security=False) -- causava
        # over-refusal grave em modelos locais pequenos (ex.: recusar "descreva
        # uma dinamica molecular" como se fosse "substancia perigosa"). Para um
        # app pessoal de um PhD em bio, o filtro era net-negativo. O never-commit
        # segue garantido pelo GATE de git no codigo (nao depende do prompt).
        system = compose_system(
            system_prompts.get(mode, system_prompts["chat"]),
            hint=context.get("system_hint", "") or "",
            style_block=_style, security=False, stage="output")

        try:
            return self.llm.chat(query, system=system, model=model, temperature=temp)
        except Exception as e:
            self.log.error(f"Gateway erro: {e}")
            return f"[Gateway] Erro ao processar: {e}"

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "lilo_chat",
                "description": "Chat geral com o LILO — fallback para qualquer pergunta não roteada para subagentes especializados.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Pergunta ou comando para o LILO"},
                        "mode": {
                            "type": "string",
                            "enum": ["chat", "code", "bioinfo", "sql"],
                            "description": "Modo de resposta (padrão: chat)",
                        },
                        "model": {"type": "string", "description": "Modelo LLM específico (opcional)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "lilo_health",
                "description": "Verifica status de todos os backends LLM (Ollama, LiteLLM, Anthropic).",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "lilo_models",
                "description": "Lista todos os modelos disponíveis no backend ativo.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def health(self):
        return self.llm.health()

    def list_models(self):
        return self.llm.list_models()
