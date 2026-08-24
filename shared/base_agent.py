"""shared/base_agent.py - Interface padronizada para subagentes LILO.

V8 (2026-05-14): capabilities() consultado pelo Villa_Lobos para
roteamento explainable.
"""

from abc import ABC, abstractmethod
from typing import Any
from .logger import get_logger


class BaseAgent(ABC):
    """Interface base para todos os subagentes LILO."""

    name: str = "base"
    description: str = "Agente base LILO."

    def __init__(self):
        self.log = get_logger(self.__class__.__name__)
        self.log.info(f"Subagente '{self.name}' inicializado.")

    @abstractmethod
    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_tools(self) -> list[dict]:
        raise NotImplementedError

    def health(self) -> dict:
        return {"agent": self.name, "status": "ok"}

    def capabilities(self) -> dict:
        """Manifesto V8 consultado por Villa_Lobos.

        Default usa self.name como domain, e resolve as keywords nesta ordem:
        1. self.keywords (lowercase)  2. self.KEYWORDS (legado uppercase)
        3. fallback a config/villa/domains.yaml. Introspecta get_tools() e
        expoe os atributos de roteamento custo/latencia (V9 2026-05-22).
        """
        tools = []
        try:
            tools = [t.get("name", "") for t in (self.get_tools() or [])]
        except Exception:
            tools = []

        # V9 (2026-05-22): aceitar tanto `keywords` quanto o legado `KEYWORDS`.
        # Antes so `keywords` (lowercase) era lido, mas todos os subagentes
        # declaram `KEYWORDS` (uppercase) -> as listas curadas eram ignoradas
        # e tudo caia no fallback do YAML. Agora ambas as convencoes valem.
        kws = list(getattr(self, "keywords", []) or [])
        if not kws:
            kws = list(getattr(self, "KEYWORDS", []) or [])
        if not kws:
            try:
                from agents.villa_lobos.agent import get_domain_keywords
                kws = list(get_domain_keywords().get(self.name, []) or [])
            except Exception:
                kws = []

        # V10.3 (2026-05-31): manifesto enriquecido p/ roteamento granular
        # (proposta secao 6 do relat. 2026-05-30). Expoe:
        #  - latency_hint: derivado de self.latency_class (fast|medium|slow),
        #    ate aqui declarado por TODOS os subagentes mas ignorado pelo manifesto;
        #  - cost_hint: alias semantico de cost_tier (ollama=low, claude_*=high);
        #  - inputs/outputs: contrato declarado (default generico, sobrescrevivel
        #    via self.inputs / self.outputs). Mantem retrocompat: as chaves antigas
        #    (cost_tier, local_only) seguem presentes.
        latency_class = getattr(self, "latency_class", "medium")
        cost_tier = getattr(self, "cost_tier", "ollama")
        cost_hint = "low" if str(cost_tier).startswith("ollama") else "high"
        return {
            "domain": getattr(self, "name", "base"),
            "keywords": kws,
            "tools": tools,
            "cost_tier": cost_tier,
            "cost_hint": cost_hint,
            "latency_class": latency_class,
            "latency_hint": latency_class,
            "local_only": getattr(self, "local_only", True),
            "inputs": list(getattr(self, "inputs", ["text"]) or ["text"]),
            "outputs": list(getattr(self, "outputs", ["text"]) or ["text"]),
            "description": getattr(self, "description", ""),
        }

    def resolve_model(self, context, chosen):
        """V18 QW2 (fase 1: so observabilidade) — retorna `chosen` INALTERADO
        e loga a divergencia vs a decisao do Policy Engine.

        lilo.route grava a decisao em context['_model']/context['_tier'] desde
        a origem, mas nenhum subagente lia essas chaves — cada um escolhe o
        proprio modelo (varios com default cloud que a policy nem modela).
        Antes de FORCAR a decisao (enforcement fica para o catalogo de
        modelos, item E1 de docs/tecnico/analise_open_agent_studio.md),
        medimos a divergencia real em log. Nao muda comportamento.
        """
        ctx = context or {}
        policy_model = ctx.get("_model")
        if policy_model and chosen and policy_model != chosen:
            self.log.info(
                "modelo: policy sugeriu %s (tier=%s); agente '%s' usara %s",
                policy_model, ctx.get("_tier", "?"), self.name, chosen)
        return chosen

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
