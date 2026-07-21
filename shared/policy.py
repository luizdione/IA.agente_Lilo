"""
shared/policy.py — Policy Engine do LILO
==========================================
Decide qual modelo usar com base em:
  1. Tipo de tarefa (trivial → sem LLM, simples → Ollama, complexo → Claude)
  2. Tamanho do input (curto/médio/longo)
  3. Override explícito do usuário (\\lilo opus, \\lilo local, etc.)
  4. Fallback automático (Ollama → Sonnet → Opus)
  5. Orçamento (custo acumulado no dia)

Uso:
    from shared.policy import PolicyEngine, ExecutionTier
    engine = PolicyEngine()
    decision = engine.decide("minha query aqui", context={})
    # decision.tier → ExecutionTier.OLLAMA
    # decision.model → "llama3.1:8b-instruct-q8_0"
    # decision.reason → "query curta, modo chat → Ollama local"
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .utils import get_env
from .logger import get_logger

log = get_logger("Policy")


class ExecutionTier(str, Enum):
    """Tiers de execução em ordem crescente de custo."""
    NO_LLM = "no_llm"
    OLLAMA_FAST = "ollama_fast"
    OLLAMA = "ollama"
    OLLAMA_HEAVY = "ollama_heavy"
    CLAUDE_SONNET = "claude_sonnet"
    CLAUDE_OPUS = "claude_opus"


# Custo estimado por 1K tokens (input + output médio)
COST_PER_1K = {
    ExecutionTier.NO_LLM: 0.0,
    ExecutionTier.OLLAMA_FAST: 0.0,
    ExecutionTier.OLLAMA: 0.0,
    ExecutionTier.OLLAMA_HEAVY: 0.0,
    ExecutionTier.CLAUDE_SONNET: 0.006,
    ExecutionTier.CLAUDE_OPUS: 0.045,
}

# Modelo padrão por tier. Modelos locais vêm de shared/models.py (fonte única);
# os Claude ficam aqui por serem específicos do tier cloud.
from shared.models import MODELS  # noqa: E402
TIER_MODELS = {
    ExecutionTier.NO_LLM: None,
    ExecutionTier.OLLAMA_FAST: MODELS["autocomplete"],
    ExecutionTier.OLLAMA: MODELS["chat"],
    ExecutionTier.OLLAMA_HEAVY: MODELS["code"],
    # Atualizado 2026-05-07 para Claude 4.5/4.6 (familia atual).
    # Variavel LILO_CLAUDE_SONNET / LILO_CLAUDE_OPUS permitem override
    # sem editar codigo (importante quando Anthropic publicar novas versoes).
    ExecutionTier.CLAUDE_SONNET: get_env("LILO_CLAUDE_SONNET", "claude-sonnet-4-5"),
    ExecutionTier.CLAUDE_OPUS: get_env("LILO_CLAUDE_OPUS", "claude-opus-4-5"),
}


@dataclass
class Decision:
    """Resultado da decisão do Policy Engine."""
    tier: ExecutionTier
    model: Optional[str]
    reason: str
    estimated_cost: float = 0.0
    override: bool = False
    subagent: Optional[str] = None


@dataclass
class PolicyConfig:
    """Configuração do Policy Engine (editável via .env ou dashboard)."""
    daily_budget_usd: float = float(get_env("LILO_DAILY_BUDGET", "1.0"))
    max_single_cost_usd: float = float(get_env("LILO_MAX_SINGLE_COST", "0.50"))
    short_threshold: int = 200
    medium_threshold: int = 2000
    long_threshold: int = 8000
    prefer_local: bool = True
    allow_cloud: bool = bool(get_env("ANTHROPIC_API_KEY", ""))


# ── Detecção de tarefas sem LLM ─────────────────────────────────────────────

NO_LLM_PATTERNS = [
    r"^(listar?|list)\s+(arquivos|files|tabelas|tables|pdfs|modelos)",
    r"^(health|status|diagnóstico|ping)",
    r"^\s*SELECT\s+.+\s+FROM\s+",
    r"^(versão|version|ajuda|help)$",
]

# Palavras que indicam complexidade alta
COMPLEX_INDICATORS = [
    "analise critica", "revisao sistematica", "meta-analise",
    "arquitetura", "design pattern", "refatorar sistema",
    "comparar abordagens", "trade-offs", "pipeline completo",
    "plano detalhado", "estrategia",
    # Estatística / Data Science
    "anova", "regressao", "regression", "clustering", "pca",
    "machine learning", "deep learning", "classificacao",
    "correlacao", "t-test", "chi-quadrado", "bootstrap",
    # Bioinformática
    "blast", "alinhamento", "docking", "molecular dynamics",
    "phylogen", "transcriptom", "proteom", "genom",
    # Dinâmica molecular / química computacional (adicionado 2026-05-06)
    "openmm", "gromacs", "amber", "namd", "charmm",
    "nvt", "npt", "equilibration", "minimization",
    "force field", "forcefield", "trajectory",
    "rmsd", "rmsf", "radius of gyration", "sasa",
    "mmgbsa", "mmpbsa", "umbrella sampling", "free energy",
    "steered md", "metadynamics", "pmf", "well-tempered",
    "particle coordinate",
    # Análise complexa
    "analise completa", "analise estatistica",
    "multiple", "multivariada",
    # Prism AI / Análise científica
    "prism", "graphpad", "pzfx", "publicacao cientifica",
    "grafico cientifico", "boxplot com pontos",
    "shapiro-wilk", "levene", "mann-whitney",
    "kruskal-wallis", "post-hoc", "bonferroni",
    "effect size", "tamanho de efeito", "cohen",
    "dados experimentais", "comparar grupos",
]

# Palavras que indicam tarefa simples
SIMPLE_INDICATORS = [
    "traduzir", "translate", "listar", "list", "formatar",
    "converter", "contar", "count", "renomear",
    "o que e", "defina", "explique brevemente",
]


# ── Normalização de acentos ─────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Remove acentos para matching robusto."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


# ── Policy Engine ────────────────────────────────────────────────────────────

_engine = None

def get_policy_engine() -> "PolicyEngine":
    global _engine
    if _engine is None:
        _engine = PolicyEngine()
    return _engine


class PolicyEngine:
    """Motor de decisão de roteamento de modelos."""

    def __init__(self, config: PolicyConfig = None):
        self.config = config or PolicyConfig()
        # V16: a fonte de verdade do gasto do dia e o CostTracker (SQLite,
        # PERSISTENTE), lido lazy por _today_cost() -> sobrevive a restart e faz
        # rollover de data sozinho. _daily_cost vira FALLBACK em-processo, usado
        # so quando a telemetria esta desabilitada (DB read-only).
        self._daily_cost = 0.0
        log.info(f"PolicyEngine init | budget=${self.config.daily_budget_usd}/dia | cloud={'ON' if self.config.allow_cloud else 'OFF'}")

    def _today_cost(self) -> float:
        """Gasto (estimado) de HOJE. Fonte de verdade = CostTracker persistente.
        FAIL-SAFE: se a telemetria estiver desabilitada (DB nao-gravavel), cai no
        acumulador em-processo (_daily_cost) -- degradado, mas NUNCA libera gasto
        cloud ilimitado (nao fail-open)."""
        try:
            from .cost_tracker import get_tracker
            summ = get_tracker().daily_summary()
            if summ and not summ.get("disabled"):
                return float(summ.get("total_cost_usd", 0.0))
            log.debug("budget: telemetria desabilitada -> fallback em-processo")
        except Exception as e:
            log.debug("budget: leitura do CostTracker falhou (%s); fallback", e)
        return self._daily_cost

    def decide(
        self,
        query: str,
        context: Optional[dict] = None,
        subagent: Optional[str] = None,
    ) -> Decision:
        """
        Decide o tier de execução para uma query.

        Args:
            query    — texto do usuário
            context  — metadados (mode, file_path, etc.)
            subagent — subagente já detectado ("sql", "pdf", "scholar", "gateway")

        Returns:
            Decision com tier, modelo, razão e custo estimado.
        """
        ctx = context or {}

        # 1. Override explícito do usuário
        override = self._parse_override(query)
        if override:
            return override

        # 2. Sem LLM (resposta direta)
        if self._is_no_llm(query):
            return Decision(
                tier=ExecutionTier.NO_LLM,
                model=None,
                reason="Tarefa direta — sem necessidade de LLM",
                subagent=subagent,
            )

        # 3. Análise de complexidade
        complexity = self._assess_complexity(query, ctx)
        input_len = len(query)

        # 4. Decisão por complexidade + tamanho
        if complexity == "trivial":
            tier = ExecutionTier.OLLAMA_FAST
            reason = "Tarefa trivial → modelo local rápido"
        elif complexity == "simple":
            tier = ExecutionTier.OLLAMA
            reason = "Tarefa simples → Ollama local"
        elif complexity == "medium":
            if input_len > self.config.long_threshold:
                tier = ExecutionTier.OLLAMA_HEAVY
                reason = "Complexidade média + input longo → modelo local pesado"
            else:
                tier = ExecutionTier.OLLAMA
                reason = "Complexidade média → Ollama local"
        elif complexity == "complex":
            if self.config.allow_cloud and self._budget_allows(ExecutionTier.CLAUDE_SONNET, input_len):
                tier = ExecutionTier.CLAUDE_SONNET
                reason = "Tarefa complexa → Claude Sonnet"
            else:
                tier = ExecutionTier.OLLAMA_HEAVY
                reason = "Tarefa complexa mas sem budget cloud → modelo local pesado"
        else:  # "critical"
            if self.config.allow_cloud and self._budget_allows(ExecutionTier.CLAUDE_OPUS, input_len):
                tier = ExecutionTier.CLAUDE_OPUS
                reason = "Tarefa crítica → Claude Opus"
            elif self.config.allow_cloud and self._budget_allows(ExecutionTier.CLAUDE_SONNET, input_len):
                tier = ExecutionTier.CLAUDE_SONNET
                reason = "Tarefa crítica mas budget insuficiente para Opus → Sonnet"
            else:
                tier = ExecutionTier.OLLAMA_HEAVY
                reason = "Tarefa crítica mas sem budget cloud → modelo local pesado"

        # 5. Ajuste por subagente
        tier, reason = self._adjust_for_subagent(tier, reason, subagent, ctx)

        # 6. Modelo e custo
        model = TIER_MODELS.get(tier)
        tokens_est = max(input_len // 4, 100)
        estimated_cost = COST_PER_1K.get(tier, 0.0) * (tokens_est / 1000)

        return Decision(
            tier=tier,
            model=model,
            reason=reason,
            estimated_cost=estimated_cost,
            subagent=subagent,
        )

    def record_cost(self, cost: float):
        """Registra custo de uma chamada (mantem o fallback em-processo em dia).
        A persistencia real e do CostTracker (gravado em lilo.route)."""
        self._daily_cost += cost
        spent = self._today_cost()
        if spent >= self.config.daily_budget_usd * 0.9:
            log.warning(f"Budget quase esgotado: ${spent:.4f} / ${self.config.daily_budget_usd}")

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.config.daily_budget_usd - self._today_cost())

    def reset_daily(self):
        """Reseta o fallback em-processo. (O rollover diario real e automatico:
        _today_cost le daily_summary do dia corrente no CostTracker.)"""
        self._daily_cost = 0.0

    # ── Métodos privados ─────────────────────────────────────────────────────

    def _parse_override(self, query: str):
        """Detecta overrides do tipo \\lilo opus <query>."""
        patterns = {
            r"\\lilo\s+opus\s+(.+)": ExecutionTier.CLAUDE_OPUS,
            r"\\lilo\s+sonnet\s+(.+)": ExecutionTier.CLAUDE_SONNET,
            r"\\lilo\s+local\s+(.+)": ExecutionTier.OLLAMA,
            r"\\lilo\s+fast\s+(.+)": ExecutionTier.OLLAMA_FAST,
            r"\\lilo\s+heavy\s+(.+)": ExecutionTier.OLLAMA_HEAVY,
        }
        for pattern, tier in patterns.items():
            m = re.match(pattern, query, re.IGNORECASE)
            if m:
                return Decision(
                    tier=tier,
                    model=TIER_MODELS.get(tier),
                    reason=f"Override explícito do usuário → {tier.value}",
                    override=True,
                )
        return None

    def _is_no_llm(self, query: str) -> bool:
        """Verifica se a query pode ser resolvida sem LLM."""
        q = query.strip()
        for pattern in NO_LLM_PATTERNS:
            if re.match(pattern, q, re.IGNORECASE):
                return True
        return False

    def _assess_complexity(self, query: str, ctx: dict) -> str:
        """
        Avalia complexidade: trivial / simple / medium / complex / critical.
        Determinístico — sem LLM.
        """
        q = _normalize(query)
        score = 0

        # Tamanho do input
        if len(query) < 50:
            score += 0
        elif len(query) < 200:
            score += 1
        elif len(query) < 1000:
            score += 2
        elif len(query) < 5000:
            score += 3
        else:
            score += 4

        # Indicadores de complexidade
        for indicator in COMPLEX_INDICATORS:
            if indicator in q:
                score += 3

        # Indicadores de simplicidade
        for indicator in SIMPLE_INDICATORS:
            if indicator in q:
                score -= 1

        # Contexto: arquivo grande → mais complexo
        if ctx.get("file_path"):
            score += 1
        if ctx.get("mode") in ("introduction", "methods"):
            score += 2

        # Múltiplas perguntas
        question_marks = q.count("?")
        if question_marks > 2:
            score += 2

        # Classificar
        if score <= 0:
            return "trivial"
        elif score <= 2:
            return "simple"
        elif score <= 4:
            return "medium"
        elif score <= 7:
            return "complex"
        else:
            return "critical"

    def _adjust_for_subagent(self, tier, reason, subagent, ctx):
        """Ajusta tier baseado no subagente específico."""
        if subagent == "sql" and ctx.get("_direct_query"):
            return ExecutionTier.NO_LLM, "Query SQL direta — execução local"

        if subagent == "scholar" and tier.value.startswith("ollama"):
            if ctx.get("synthesize", True):
                return ExecutionTier.OLLAMA_HEAVY, reason + " (scholar+síntese → modelo pesado)"

        if subagent == "pdf" and ctx.get("mode") in ("introduction", "methods"):
            if tier in (ExecutionTier.OLLAMA_FAST, ExecutionTier.OLLAMA):
                return ExecutionTier.OLLAMA_HEAVY, "Análise profunda de PDF → modelo pesado"

        if subagent == "prism":
            # Prism AI: estatística é local (scipy), LLM só para writing
            if ctx.get("enhance_with_llm", True):
                if tier in (ExecutionTier.OLLAMA_FAST,):
                    return ExecutionTier.OLLAMA, "Prism AI + escrita científica → Ollama"
            else:
                return ExecutionTier.NO_LLM, "Prism AI sem LLM — scipy local"

        return tier, reason

    def _budget_allows(self, tier: ExecutionTier, input_len: int) -> bool:
        """Verifica se o budget permite usar esse tier."""
        tokens_est = max(input_len // 4, 100)
        estimated_cost = COST_PER_1K.get(tier, 0.0) * (tokens_est / 1000)
        return (self._today_cost() + estimated_cost) <= self.config.daily_budget_usd

    def get_fallback(self, tier: ExecutionTier) -> ExecutionTier:
        """Retorna o próximo tier para fallback."""
        chain = [
            ExecutionTier.OLLAMA_FAST,
            ExecutionTier.OLLAMA,
            ExecutionTier.OLLAMA_HEAVY,
            ExecutionTier.CLAUDE_SONNET,
            ExecutionTier.CLAUDE_OPUS,
        ]
        try:
            idx = chain.index(tier)
            if idx + 1 < len(chain):
                next_tier = chain[idx + 1]
                if next_tier.value.startswith("claude") and not self.config.allow_cloud:
                    return tier  # Não escalar para cloud
                return next_tier
            return tier  # Já está no máximo
        except ValueError:
            return ExecutionTier.OLLAMA  # Default

    def get_status(self) -> dict:
        """Retorna status atual do Policy Engine."""
        return {
            "daily_budget_usd": self.config.daily_budget_usd,
            "daily_cost_usd": self._today_cost(),
            "budget_remaining_usd": self.budget_remaining,
            "allow_cloud": self.config.allow_cloud,
            "prefer_local": self.config.prefer_local,
            "tiers": {t.value: TIER_MODELS.get(t, "N/A") for t in ExecutionTier},
        }
