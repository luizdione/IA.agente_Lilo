"""
Villa Lobos Agent -- Pipeline multi-agente orquestrado
======================================================
5 etapas: Orchestrator -> Planner -> Reader -> Worker -> Reporter
Cada etapa usa Ollama com modelo configuravel.
Integra-se ao LILO como BaseAgent.

2026-05-07: Sprint A -- delegate_to_specialist (LLM router + heuristica).
2026-05-07: Sprint B -- smart routing (Orchestrator emite JSON declarando
quais stages executar; tarefas triviais pulam direto para Reporter).
2026-05-12: Sprint 2 -- V1 cache LRU para _orchestrate_decision; V2 telemetria
stage-level (cost_tracker); V6 domain registry via YAML com hot-reload;
V7 metodo explain_routing (debug sem efetuar pipeline).
"""

import sys
import time
import re
import json
import hashlib
import os as _os
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client, MODELS
from shared.logger import get_logger
from shared.server_profile import get_profile_policy, get_server_profile

log = get_logger("VillaLobos")

# V9 (2026-05-22): retry adaptativo (proposta 6.3 do relatorio 2026-05-20).
# RETRY_DELAY=5s fixo penalizava o Ollama local (que falha rapido); agora
# vem de env. O circuit breaker em _call_agent ainda pula retries/sleep
# quando o backend e mock/indisponivel.
MAX_RETRIES = int(_os.getenv("VILLA_MAX_RETRIES", "2"))
RETRY_DELAY = float(_os.getenv("VILLA_RETRY_DELAY", "1.5"))

# ------------------------------------------------------------------
# V6 -- Domain registry pluggable (config/villa/domains.yaml)
# ------------------------------------------------------------------
_DOMAIN_DEFAULTS = {
    "prism":   ["prism", "anova", "t-test", "kruskal", "mann-whitney", "shapiro",
                "boxplot", "p-valor", "p-value", "comparar grupos", "experimento",
                "pzfx", "graphpad", "normalidade"],
    "sql":     ["sql", "select", "tabela", "banco", "sqlite", "mysql", "postgres",
                "join", "group by", "schema", "consulta sql"],
    "pdf":     ["pdf", "artigo", "paper", "documento", "doi", "introducao",
                "metodos", "resultados", "discussao"],
    "scholar": ["pubmed", "arxiv", "scholar", "literatura", "referencia", "papers",
                "publicacoes", "buscar artigos", "pesquisa academica", "revisao"],
    "desktop": ["arquivo local", "filesystem", "diretorio", "ler arquivo",
                "escrever arquivo", "rodar script", "executar python",
                "shell", "bash", "powershell"],
    "gateway": ["chat geral", "duvida rapida", "explique", "o que e",
                "definicao", "conceito"],
}

_DOMAINS_YAML = _ROOT / "config" / "villa" / "domains.yaml"
_DOMAINS_CACHE = {"mtime": None, "keywords": dict(_DOMAIN_DEFAULTS)}


def _load_domains_from_yaml():
    """Carrega DOMAIN_KEYWORDS de config/villa/domains.yaml com hot-reload."""
    if not _DOMAINS_YAML.exists():
        _DOMAINS_CACHE["keywords"] = dict(_DOMAIN_DEFAULTS)
        _DOMAINS_CACHE["mtime"] = None
        return _DOMAINS_CACHE["keywords"]
    try:
        mtime = _DOMAINS_YAML.stat().st_mtime
        if _DOMAINS_CACHE["mtime"] == mtime:
            return _DOMAINS_CACHE["keywords"]
        try:
            import yaml as _yaml
        except ImportError:
            log.debug("PyYAML ausente; usando defaults de DOMAIN_KEYWORDS")
            _DOMAINS_CACHE["keywords"] = dict(_DOMAIN_DEFAULTS)
            _DOMAINS_CACHE["mtime"] = mtime
            return _DOMAINS_CACHE["keywords"]
        with _DOMAINS_YAML.open("r", encoding="utf-8") as fh:
            data = _yaml.safe_load(fh) or {}
        merged = dict(_DOMAIN_DEFAULTS)
        ydomains = data.get("domains", data) if isinstance(data, dict) else {}
        if isinstance(ydomains, dict):
            for name, kws in ydomains.items():
                if isinstance(kws, list) and all(isinstance(k, str) for k in kws):
                    merged[str(name)] = [k.lower() for k in kws]
        _DOMAINS_CACHE["keywords"] = merged
        _DOMAINS_CACHE["mtime"] = mtime
        log.info("Villa: domains.yaml carregado (%d dominios)", len(merged))
        return merged
    except Exception as e:
        log.warning("Villa: falha lendo domains.yaml (%s); usando defaults", e)
        _DOMAINS_CACHE["keywords"] = dict(_DOMAIN_DEFAULTS)
        return _DOMAINS_CACHE["keywords"]


def get_domain_keywords():
    return _load_domains_from_yaml()


DOMAIN_KEYWORDS = get_domain_keywords()

_STAGE_DEFAULTS = {
    "orchestrator": "ollama_fast",
    "planner":      "ollama_plan",
    "reader":       "ollama_code",
    "worker":       "ollama_code",
    "reporter":     "ollama_chat",
}
DEFAULT_STAGE_TIERS = {
    stage: _os.getenv("VILLA_TIER_" + stage.upper(), default)
    for stage, default in _STAGE_DEFAULTS.items()
}


# V10.4 (2026-06-02): marcadores de PROFUNDIDADE que desqualificam o gateway.
# O gateway tem keywords genericas ("explique", "conceito", "o que e") que
# capturavam pedidos de explicacao APROFUNDADA (ex.: "Explique o principio da
# incerteza de Heisenberg e suas implicacoes", "Explique as principais causas
# economicas e sociais da Revolucao Francesa"). No bench multi-dominio essas
# queries eram delegadas ao chat raso (qualidade 25-28) enquanto perguntas de
# MESMA profundidade sem "explique" (quimica/biologia/matematica) seguiam o
# pipeline completo -> roteamento inconsistente. Ver bench_semantic_*.json.
_GATEWAY_DEEP_MARKERS = (
    "principa", "implicac", "mecanismo", "demonstr", "etapas", "causas",
    "fatores", "diagnostic", "manejo", "e suas ", "economic", "sociais",
    "enuncie", "aprofund", "edafoclimatic", "sinais clinic",
)


def _strip_accents(s):
    """V10.4: fold de acentos para casamento robusto em pt-BR.

    Antes, "o que e" (keyword) nao casava "o que e'" acentuado da query e
    "quimica/fisica/replicacao" acentuadas escapavam das keywords. Normalizar
    elimina essa classe de erro de roteamento por acento.
    """
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _is_deep_query(query):
    """V10.5: True se a query e NAO trivial (longa >=60 chars OU contem
    marcador de profundidade). Queries profundas JAMAIS devem ir ao chat
    raso do gateway -- exigem o pipeline completo. Helper compartilhado por
    _detect_domain e pela blindagem final de _delegate_to_specialist.
    """
    q = _strip_accents((query or "").lower())
    return len(q) >= 60 or any(m in q for m in _GATEWAY_DEEP_MARKERS)


# V11.2 (2026-06-11): marcadores que BLOQUEIAM o fast-path (skip-to-reporter).
# Sao verbos explicativos + sinais de profundidade. Diferem de _is_deep_query
# (que usa len>=60, largo demais p/ esta decisao) por serem PRECISOS: uma
# consulta factual curta-ou-longa ("Qual a capital da Franca e sua populacao?")
# NAO casa nenhum marcador e segue podendo usar o fast-path (preserva
# celeridade); ja "Explique ... e suas implicacoes" casa e exige o Worker.
_FAST_PATH_BLOCK_MARKERS = (
    # verbos de explicacao/analise aprofundada
    "explique", "explicar", "descreva", "descrever", "detalhe", "detalhar",
    "discuta", "discutir", "compare", "comparar", "analise", "avalie",
    "enumere", "elenque", "como funciona",
    # profundidade conceitual (subconjunto de _GATEWAY_DEEP_MARKERS)
    "mecanismo", "implicac", "principio", "principais", "causas", "fatores",
    "etapas", "diagnostic", "manejo", "sinais clinic", "edafoclimatic",
    "e suas ", "aprofund",
)
# Demonstracao/prova: exige Worker E mais de uma iteracao (passo de refino).
_PROOF_MARKERS = (
    "demonstr", "deduz", "deduc", "prove que", "provar que", "passo a passo",
    "derive ", "enuncie",
)

# V12 (2026-06-11): especialistas de FERRAMENTA que podem executar a etapa
# Worker do pipeline (delegacao por etapa). Exclui gateway (chat raso) e villa
# (evita recursao). Usado para validar o campo worker_agent do Orchestrator.
_STAGE_WORKER_AGENTS = frozenset({"scholar", "sql", "prism", "pdf", "desktop"})


def _block_fast_path(query):
    """V11.2: classifica a guarda anti-fast-path UNIFICADA (ramo LLM + ramo
    heuristico usavam guardas distintas e inconsistentes; bench 2026-06-11:
    fisica caiu em fast-path q=64 porque o ramo do LLM-orchestrator so cobria
    demonstracao/prova, nao explicacao/profundidade).

    Retorna:
      "proof" -> escalar fast-path -> Worker com >=2 iteracoes;
      "explain" -> escalar fast-path -> Worker com iteracoes inalteradas;
      None -> fast-path permitido (query trivial/factual).
    """
    q = _strip_accents((query or "").lower())
    if any(m in q for m in _PROOF_MARKERS):
        return "proof"
    if any(m in q for m in _FAST_PATH_BLOCK_MARKERS):
        return "explain"
    return None


def _detect_domain(query):
    q = _strip_accents((query or "").lower())
    kw_map = get_domain_keywords()
    scores = {d: sum(1 for kw in kws if _strip_accents(kw) in q)
              for d, kws in kw_map.items()}
    if not scores:
        return None
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return None
    # V10.4: rebaixa "gateway" para queries NAO triviais. Se a query e longa
    # (>=60 chars) ou tem marcador de profundidade, o gateway perde para o
    # melhor especialista NAO-gateway; se nenhum casa, retorna None -> Villa
    # roda o pipeline completo (resposta tecnica) em vez do chat raso.
    if best == "gateway":
        deep = len(q) >= 60 or any(m in q for m in _GATEWAY_DEEP_MARKERS)
        if deep:
            non_gw = {d: s for d, s in scores.items()
                      if d != "gateway" and s > 0}
            return max(non_gw, key=non_gw.get) if non_gw else None
    return best


VILLA_MODELS = {
    "orchestrator": MODELS.get("chat", "llama3.1:8b-instruct-q8_0"),
    "planner":      MODELS.get("plan", "phi3:14b-medium-128k-instruct-q4_K_M"),
    "reader":       MODELS.get("code", "qwen2.5-coder:14b"),
    "worker":       MODELS.get("code", "qwen2.5-coder:14b"),
    "reporter":     MODELS.get("chat", "llama3.1:8b-instruct-q8_0"),
}

# V10.9 (2026-06-08): selecao de modelo do WORKER/READER sensivel a INTENCAO.
# Defeito detectado na 1a corrida REAL do bench (backend=ollama): o worker
# usava o modelo de CODIGO (qwen2.5-coder:14b) para TODOS os dominios --
# inclusive biologia, quimica, fisica, historia, nutricao, agro e veterinaria
# -- onde um modelo instruct GERAL produz prosa tecnica/cientifica superior.
# Coder models sao otimizados para gerar codigo, nao explicacao discursiva.
# Agora: coder so quando a QUERY tem intencao de codigo/engenharia de dados;
# caso contrario, modelo instruct geral. Ambos overrideaveis por env.
VILLA_WORKER_GENERAL_MODEL = _os.getenv(
    "VILLA_WORKER_GENERAL_MODEL", MODELS.get("chat", "llama3.1:8b-instruct-q8_0"))
VILLA_WORKER_CODE_MODEL = _os.getenv(
    "VILLA_WORKER_CODE_MODEL", MODELS.get("code", "qwen2.5-coder:14b"))

# Marcadores (ja sem acento, minusculos) de intencao de CODIGO/dados.
_CODE_INTENT_MARKERS = (
    "codigo", "code", "python", "javascript", "typescript", "c++", "rust ",
    "sql", "select ", "regex", "script", "funcao", "def ", "class ", "classe",
    "algoritmo", "compil", "stack trace", "traceback", "debug", "refator",
    "refactor", "implementa", "pandas", "numpy", "dataframe", "endpoint",
    "json", "yaml", "bash", "powershell", "shell", "git ", "docker", "pytest",
    "unit test", "lint", ".py", ".js", ".sql", "```", "consulta sql",
    "schema", "join ", "group by",
)


def _is_code_intent(text):
    """V10.9: heuristica de intencao de CODIGO/engenharia de dados.

    True  -> manter modelo coder (qwen2.5-coder).
    False -> usar instruct geral (melhor para conhecimento/ciencia/prosa).
    Conservadora: so retorna True com sinal explicito de codigo; na duvida
    devolve False, pois a maioria das queries de conhecimento se beneficia
    do modelo geral.
    """
    t = _strip_accents((text or "").lower())
    return any(m in t for m in _CODE_INTENT_MARKERS)


def _is_multipart_query(text):
    """V11.1 (2026-06-10): detecta perguntas EXPLICATIVAS MULTI-PARTE.

    True quando a query enumera varios sub-itens distintos -- ex.:
    "Quais sao os sinais clinicos, o diagnostico e o manejo da cinomose?"
    (lista com virgula encerrada por 'e'/'ou') ou tem 2+ perguntas, ou um
    verbo explicativo + comando de enumeracao (cite/liste).

    Motivacao: num UNICO passo do Worker, esses pedidos as vezes saem FINOS
    (bench: veterinaria@1 q=48 len=734 em 2026-06-10; historia@1 q=48 em
    2026-06-09) -- a saida fica logo abaixo do limiar estrutural por nao
    cobrir todas as partes. Usado para anexar uma diretriz de COBERTURA ao
    prompt do Worker, SEM custo de iteracoes extras (preserva a celeridade,
    prioridade do Dione). So ESCALA a instrucao; nunca remove. Conservadora:
    nao dispara em pares de facetas simples ("X e Y" sem virgula), que ja
    saem bem em passo unico (historia/conhecimentos_gerais/agropecuaria).
    """
    t = _strip_accents((text or "").lower()).strip()
    if not t:
        return False
    # Regra 1: lista com virgula encerrada por conjuncao -> "X, Y e/ou Z".
    if re.search(r",\s*[^,?]*\s+(e|ou)\s+\w", t):
        return True
    # Regra 2: 2+ interrogacoes (multiplas perguntas no mesmo enunciado).
    if t.count("?") >= 2:
        return True
    # Regra 3: verbo explicativo + comando de enumeracao explicito.
    _enum = ("cite", "liste", "enumere", "elenque")
    _expl = ("explique", "descreva", "detalhe", "discuta", "quais", "como ")
    if any(k in t for k in _enum) and any(k in t for k in _expl):
        return True
    return False


# V11.2 (2026-06-11): EXPERT_SYSTEM domain-adaptativo. Antes forcava
# "mecanismos moleculares, enzimas, vias metabolicas" em TODA query -- otimo
# para biologia, mas degradava historia/geografia/matematica/fisica no bench
# multi-dominio (a IA tentava enquadrar tudo em vias de sinalizacao). Agora a
# instrucao de vocabulario tecnico e ENUMERADA POR DOMINIO: cada area recebe o
# registro correto, preservando o perfil do usuario (PhD bio + cientista de
# dados) sem impor o vies biologico onde nao cabe.
EXPERT_SYSTEM = (
    "Voce e o agente {role} do pipeline Villa Lobos no LILO. "
    "O usuario e um PhD em Biologia Molecular e Cientista de Dados senior. "
    "NUNCA simplifique como se fosse para leigos. Use SEMPRE terminologia "
    "tecnica precisa e o vocabulario proprio do DOMINIO da pergunta: "
    "equacoes, teoremas e demonstracoes em exatas (fisica/matematica); "
    "mecanismos de reacao e nomenclatura em quimica; enzimas, vias e "
    "biomoleculas em biologia; metodos, dados e causas em "
    "historia/geografia/economia/agro; metodos estatisticos e algoritmos "
    "pelo nome correto em ciencia de dados. "
    "Responda de forma direta, tecnica e aprofundada. "
    "Use notacao cientifica e equacoes quando apropriado. "
    "Quando relevante, cite referencias (PMID, DOI, fontes). "
    "Responda em portugues brasileiro."
)


class VillaLobosAgent(BaseAgent):
    """Pipeline multi-agente local (100% Ollama) com smart routing."""

    name = "villa"
    description = (
        "Pipeline multi-agente Villa Lobos: Orchestrator -> Planner -> "
        "Reader -> Worker -> Reporter. Smart routing pula stages "
        "desnecessarios para tarefas triviais."
    )

    _SIMPLE_PATTERNS = [
        r"^o que (e|sao)\b", r"^what is\b", r"^what are\b",
        r"^como (se|funciona|definir)\b", r"^how (does|to)\b",
        r"^defina\b", r"^define\b",
        r"^explique (em )?(uma|poucas) (frase|linha)",
        r"^qual (e|a|o) (significado|definicao|diferenca)\b",
        r"\bconverter? \d", r"\bquantos? \w+ (em|tem)\b",
        r"^calcule \d", r"^calculate \d",
    ]

    # V10.3 (2026-05-31): pedidos de EXPLICACAO/aprofundamento. Quando
    # presentes, a query NUNCA e trivial -- mesmo curta e mesmo casando um
    # _SIMPLE_PATTERN (ex.: "Como funciona a replicacao do DNA? Cite etapas").
    # Corrige roteamento multi-dominio: antes, perguntas explicativas curtas
    # caiam em fast-path (skip_to_reporter) e respondiam raso. Ver
    # scripts/bench_semantic_domains.py e RELATORIO 2026-05-31.
    _EXPLAIN_KW = (
        "explique", "explicar", "descreva", "descrever", "demonstre",
        "demonstrar", "detalhe", "detalhar", "discuta", "compare",
        "analise", "avalie", "quais", "por que", "porque", "cite",
        "enumere", "enuncie", "como funciona", "mecanismo", "causas",
        "fatores", "etapas", "implicac", "sinais clinic",
    )

    _CACHE_MAX = 256

    def __init__(self):
        super().__init__()
        self.client = get_client()
        self._decision_cache = OrderedDict()
        self._decision_cache_hits = 0
        self._decision_cache_misses = 0

    @staticmethod
    def _normalize_query_for_cache(query):
        q = re.sub(r"\s+", " ", (query or "").strip().lower())
        return hashlib.sha1(q[:512].encode("utf-8")).hexdigest()

    def _decision_cache_get(self, key):
        if key in self._decision_cache:
            self._decision_cache.move_to_end(key)
            self._decision_cache_hits += 1
            return dict(self._decision_cache[key])
        self._decision_cache_misses += 1
        return None

    def _decision_cache_put(self, key, value):
        if key in self._decision_cache:
            self._decision_cache.move_to_end(key)
        self._decision_cache[key] = dict(value)
        while len(self._decision_cache) > self._CACHE_MAX:
            self._decision_cache.popitem(last=False)

    def cache_stats(self):
        total = self._decision_cache_hits + self._decision_cache_misses
        ratio = (self._decision_cache_hits / total) if total else 0.0
        return {
            "hits": self._decision_cache_hits,
            "misses": self._decision_cache_misses,
            "size": len(self._decision_cache),
            "max": self._CACHE_MAX,
            "hit_ratio": round(ratio, 3),
        }

    def run(self, query, context=None):
        if context is None:
            context = {}
        t0 = time.time()
        # V9.4 (2026-05-30): inicializar stage_timings (perdido em
        # truncamento anterior); referenciado por Planner/Reader/Worker/Reporter.
        stage_timings = {}
        base_path = context.get("base_path", str(_ROOT))
        iterations = context.get("iterations", 1)
        use_reader = context.get("use_reader", True)
        allow_delegate = context.get("allow_delegate", True)

        # V10.3 (2026-05-31): streaming entre stages (proposta secao 6).
        # Se o chamador passar context["stream_callback"], cada stage emite
        # eventos (start/done) assim que conclui -- consumido por
        # /v1/villa/run/stream para SSE stage-a-stage. No-op se ausente.
        _cb = context.get("stream_callback")

        def _emit(stage, status, ms=None, preview=None):
            if not _cb:
                return
            try:
                _cb(stage, status, ms,
                    (preview[:160] if isinstance(preview, str) else preview))
            except Exception as _ce:  # nunca deixar telemetria quebrar pipeline
                log.debug("stream_callback falhou: %s", _ce)

        log.info("Pipeline Villa Lobos: %s...", query[:80])
        # V10.9: intencao de codigo decidida pela QUERY ORIGINAL (robusto a
        # scaffolding dos prompts) -> escolhe coder vs instruct geral no worker.
        self._cur_code_intent = _is_code_intent(query)

        if allow_delegate:
            specialist = self._delegate_to_specialist(query, context)
            if specialist:
                duration = time.time() - t0
                lines = [
                    "## Villa Lobos -- Delegacao a Especialista",
                    "**Tarefa:** " + query,
                    "**Especialista:** " + specialist["agent"],
                    "**Roteamento:** " + specialist.get("route_method", "?"),
                    "**Duracao:** %.1fs" % duration,
                    "",
                    "### Resultado",
                    specialist["result"],
                ]
                return "\n".join(lines)

        try:
            log.info("  Stage 1/5: Orchestrator (smart routing)")
            _so = time.time()
            decision = self._orchestrate_decision(query)
            _emit("orchestrator", "done", round((time.time() - _so) * 1000),
                  decision.get("reasoning"))
            log.info(
                "    decision: complex=%s plan=%s read=%s work=%s iters=%d skip=%s",
                decision.get("complexity"),
                decision.get("needs_planning"),
                decision.get("needs_reader"),
                decision.get("needs_worker"),
                int(decision.get("iterations", 1)),
                decision.get("skip_to_reporter"),
            )

            for k in ("needs_planning", "needs_reader", "needs_worker",
                      "skip_to_reporter"):
                if k in context:
                    decision[k] = bool(context[k])
            if "iterations" in context:
                decision["iterations"] = int(context["iterations"])
            else:
                decision["iterations"] = int(decision.get("iterations", iterations))

            if decision.get("skip_to_reporter"):
                log.info("  Smart routing: SKIP-TO-REPORTER (tarefa simples)")
                fast_prompt = (
                    "Responda diretamente a pergunta abaixo de forma tecnica, "
                    "concisa e precisa. Nivel: pesquisador senior. "
                    "Sem secoes 'Resumo Executivo', 'Discussao Critica' etc. "
                    "Apenas a resposta tecnica direta.\n\n"
                    "PERGUNTA: " + query
                )
                _sf = time.time()
                fast_result = self._call_agent("reporter", fast_prompt)
                _emit("reporter", "done", round((time.time() - _sf) * 1000),
                      "fast-path")
                duration = time.time() - t0
                log.info("  Pipeline FAST concluido em %.1fs", duration)
                lines = [
                    "## Villa Lobos -- Fast Path",
                    "**Tarefa:** " + query,
                    "**Roteamento:** skip-to-reporter (%s)" % (
                        (decision.get("reasoning") or "")[:120]),
                    "**Duracao:** %.1fs" % duration,
                    "",
                    "### Resposta",
                    fast_result,
                ]
                return "\n".join(lines)

            orch_result = (
                "complexity=%s; plan=%s; read=%s; work=%s; "
                "iters=%s; reasoning=%s" % (
                    decision.get("complexity"),
                    decision.get("needs_planning"),
                    decision.get("needs_reader"),
                    decision.get("needs_worker"),
                    decision.get("iterations"),
                    (decision.get("reasoning") or "")[:200],
                )
            )

            plan_result = ""
            _t = time.time()
            if decision.get("needs_planning", True):
                log.info("  Stage 2/5: Planner")
                plan_prompt = (
                    "Crie um plano detalhado e tecnico para executar a tarefa. "
                    "Inclua: abordagem metodologica, ferramentas/algoritmos, "
                    "metricas de avaliacao, e potenciais limitacoes. "
                    "Nivel: pesquisador senior.\n\n"
                    "TAREFA: " + query + "\n\n"
                    "ANALISE DO ORQUESTRADOR:\n" + orch_result[:800]
                )
                plan_result = self._call_agent("planner", plan_prompt)
                stage_timings["planner"] = round(time.time() - _t, 3)
                _emit("planner", "done", int(stage_timings["planner"] * 1000),
                      plan_result)
            else:
                log.info("  Stage 2/5: Planner (pulado)")
                stage_timings["planner"] = 0.0

            effective_use_reader = (
                use_reader if "use_reader" in context
                else decision.get("needs_reader", use_reader)
            )
            reader_result = ""
            _t = time.time()
            if effective_use_reader:
                log.info("  Stage 3/5: Reader")
                reader_prompt = (
                    "Analise o plano e identifique informacoes adicionais "
                    "necessarias. Liste arquivos, dados ou contexto relevante.\n\n"
                    "PLANO:\n" + plan_result[:800] + "\n\n"
                    "DIRETORIO BASE: " + base_path
                )
                reader_result = self._call_agent("reader", reader_prompt)
                stage_timings["reader"] = round(time.time() - _t, 3)
                _emit("reader", "done", int(stage_timings["reader"] * 1000),
                      reader_result)
            else:
                log.info("  Stage 3/5: Reader (pulado)")
                stage_timings["reader"] = 0.0

            effective_iterations = int(decision.get("iterations", iterations))
            # V9.1 (2026-05-23): respeitar o teto de iteracoes do perfil do
            # servidor (LILO_SERVER_PROFILE). O MESMO Villa roda menos iteracoes
            # em perfis enxutos (cowork/bio/pycharm=2) e mais em desktop=3 --
            # "atuar... de acordo com o setup do servidor".
            _max_it = get_profile_policy().get("max_iterations")
            if _max_it:
                _capped = max(1, min(effective_iterations, int(_max_it)))
                if _capped != effective_iterations:
                    log.info("  Perfil '%s': iters %d -> %d (teto do servidor)",
                             get_server_profile(), effective_iterations, _capped)
                effective_iterations = _capped
            work_results = []
            _t = time.time()
            if decision.get("needs_worker", True):
                log.info("  Stage 4/5: Worker (iters=%d)", effective_iterations)
                # V11.1 (2026-06-10): diretriz de COBERTURA para perguntas
                # multi-parte (ex.: veterinaria "sinais, diagnostico e manejo").
                # Anexada ao prompt do Worker; custo ~0 (sem iteracoes extras),
                # preserva celeridade. So ESCALA a instrucao, nunca remove.
                _mp_nudge = (
                    "Esta tarefa tem MULTIPLAS PARTES/sub-perguntas. Responda "
                    "CADA parte de forma explicita e completa, com um subtitulo "
                    "curto por parte (ex.: '### <parte>'). Nao omita nenhuma.\n\n"
                    if _is_multipart_query(query) else ""
                )
                if _mp_nudge:
                    log.info("    V11.1: nudge multi-parte ATIVO")
                # V12 (2026-06-11): delegacao por ETAPA. Se o Orchestrator
                # indicou um especialista (worker_agent), a 1a iteracao do
                # Worker e executada por ELE (ex.: scholar busca literatura,
                # prism analisa .xlsx) e o Reporter sintetiza -- "compartilhar
                # etapas entre subagentes". Desligavel via LILO_STAGE_DELEGATION=0.
                _stage_agent = decision.get("worker_agent")
                _stage_map = None
                if _stage_agent and _os.getenv("LILO_STAGE_DELEGATION", "1") == "1":
                    try:
                        from lilo import _load_agents
                        _stage_map = _load_agents()
                        if _stage_agent not in _stage_map:
                            _stage_agent = None
                    except Exception as _le:
                        log.warning("    V12: _load_agents falhou (%s)", _le)
                        _stage_agent = None
                else:
                    _stage_agent = None
                if _stage_agent:
                    log.info("    V12: Worker delega a especialista '%s'",
                             _stage_agent)
                for i in range(effective_iterations):
                    iter_ctx = (
                        " (iteracao %d/%d)" % (i + 1, effective_iterations)
                        if effective_iterations > 1 else ""
                    )
                    # V11.2: instrucao de profundidade NEUTRA por dominio (antes
                    # impunha "mecanismos moleculares, proteinas/genes, vias de
                    # sinalizacao" a TODA query -- vies bio que degradava
                    # historia/geografia/matematica). O detalhe especifico cabe
                    # ao EXPERT_SYSTEM (enumerado por dominio).
                    worker_prompt = (
                        "Execute a tarefa abaixo" + iter_ctx + ". "
                        "Seja rigoroso, tecnico e aprofundado, no nivel de um "
                        "pesquisador senior da area. Fundamente com dados "
                        "quantitativos, equacoes, nomenclatura tecnica correta e "
                        "exemplos concretos do dominio quando aplicavel.\n\n"
                        "TAREFA ORIGINAL: " + query + "\n\n"
                        + _mp_nudge
                    )
                    # V11.2 (#7): so injeta plano/contexto se forem uteis -- um
                    # stub de erro ("[planner ERRO...]" / "[reader ERRO...]") nao
                    # deve virar "PLANO"/"CONTEXTO" e poluir o prompt do Worker.
                    if plan_result and not plan_result.lstrip().startswith("["):
                        worker_prompt += "PLANO:\n" + plan_result[:800] + "\n\n"
                    if reader_result and not reader_result.lstrip().startswith("["):
                        worker_prompt += "CONTEXTO:\n" + reader_result[:400] + "\n\n"
                    if work_results:
                        worker_prompt += (
                            "RESULTADO ANTERIOR:\n" + work_results[-1][:400] + "\n\n"
                        )
                    _wi = time.time()
                    if _stage_agent and i == 0:
                        # 1a iteracao executada pelo especialista indicado.
                        try:
                            w_result = _stage_map[_stage_agent].run(
                                query, dict(context or {}))
                            log.info("    Worker[it1] via especialista '%s'",
                                     _stage_agent)
                        except Exception as _se:
                            log.warning("    especialista %s falhou (%s); "
                                        "Worker LLM", _stage_agent, _se)
                            w_result = self._call_agent("worker", worker_prompt)
                    else:
                        w_result = self._call_agent("worker", worker_prompt)
                    work_results.append(w_result)
                    # V10.3: emite cada iteracao do Worker assim que conclui
                    # (granularidade que o Reporter/cliente pode ir consumindo).
                    _emit("worker", "iteration",
                          round((time.time() - _wi) * 1000), w_result)
                stage_timings["worker"] = round(time.time() - _t, 3)
                _emit("worker", "done", int(stage_timings["worker"] * 1000),
                      "iters=%d" % effective_iterations)
            else:
                log.info("  Stage 4/5: Worker (pulado)")
                stage_timings["worker"] = 0.0

            _t = time.time()
            log.info("  Stage 5/5: Reporter")
            combined_work = "\n---\n".join(work_results) if work_results else ""
            report_prompt = (
                "Sintetize os resultados em um relatorio tecnico-cientifico. "
                "Formato: Resumo Executivo, Resultados Principais, "
                "Discussao Critica, Proximos Passos, Referencias. "
                "Nivel: paper cientifico, nao divulgacao.\n\n"
                "TAREFA: " + query + "\n\n"
            )
            if plan_result:
                report_prompt += "PLANO EXECUTADO:\n" + plan_result[:600] + "\n\n"
            if combined_work:
                report_prompt += "RESULTADOS DO WORKER:\n" + combined_work[:2000]
            report_result = self._call_agent("reporter", report_prompt)
            stage_timings["reporter"] = round(time.time() - _t, 3)
            _emit("reporter", "done", int(stage_timings["reporter"] * 1000),
                  report_result)

            duration = time.time() - t0
            log.info("  Pipeline concluido em %.1fs (timings=%s)",
                     duration, stage_timings)

            stages_executed = ["orchestrator"]
            if decision.get("needs_planning", True):
                stages_executed.append("planner")
            if effective_use_reader:
                stages_executed.append("reader")
            if decision.get("needs_worker", True):
                stages_executed.append("worker")
            stages_executed.append("reporter")

            _timings_str = ", ".join(
                "%s=%.2fs" % (k, stage_timings.get(k, 0.0))
                for k in stages_executed if k in stage_timings
            )
            lines = [
                "## Villa Lobos -- Pipeline (smart routing)",
                "**Tarefa:** " + query,
                "**Duracao:** %.1fs | **Iteracoes:** %d" % (
                    duration, effective_iterations),
                "**Stages:** " + " -> ".join(stages_executed),
                "**Tempos:** " + _timings_str,
                "**Roteamento:** " + (decision.get("reasoning") or "")[:200],
                "",
                "### Plano",
                plan_result[:800] if plan_result else "(pulado)",
                "",
                "### Resultado",
                combined_work[:1500] if combined_work else "(pulado)",
                "",
                "### Relatorio",
                report_result[:1500],
            ]
            return "\n".join(lines)

        except Exception as e:
            duration = time.time() - t0
            log.error("Pipeline falhou em %.1fs: %s", duration, e)
            return "## Villa Lobos -- Erro\n\n%s\n\nDuracao: %.1fs" % (e, duration)

    def _orchestrate_decision(self, query, use_cache=True):
        """Smart routing: Orchestrator emite JSON declarando stages.

        V1 (2026-05-12): cache LRU bounded por hash da query normalizada.
        """
        cache_key = self._normalize_query_for_cache(query) if use_cache else None
        if cache_key:
            cached = self._decision_cache_get(cache_key)
            if cached is not None:
                cached["_cache"] = "hit"
                log.debug("Orchestrator cache HIT")
                return cached

        prompt = (
            "Voce e o Orchestrator do pipeline Villa Lobos. Sua tarefa "
            "e classificar a tarefa abaixo e decidir quais estagios do "
            "pipeline (Planner, Reader, Worker) sao necessarios.\n\n"
            "Estagios:\n"
            "- Planner: cria plano metodologico (custo: 1 chamada LLM).\n"
            "- Reader: identifica arquivos/contexto a consultar.\n"
            "- Worker: executa a tarefa (1-3 iteracoes).\n"
            "- Reporter: sempre executa.\n\n"
            "Quando pular:\n"
            "- skip_to_reporter=true: pergunta factual, definicao, "
            "conversao de unidades, calculo simples.\n"
            "- needs_planning=false: tarefa direta sem necessidade de plano.\n"
            "- needs_reader=false: nao referencia arquivos/dados.\n"
            "- needs_worker=false: Reporter sozinho responde.\n\n"
            "Delegacao de especialista (V12, opcional):\n"
            "- worker_agent: se a EXECUCAO (Worker) se beneficiar de um "
            "especialista, indique UM dentre [scholar, sql, prism, pdf, "
            "desktop]; senao null. scholar=buscar literatura (PubMed/arXiv); "
            "sql=consulta/estatistica em banco; prism=analise estatistica de "
            ".xlsx/.csv; pdf=sumarizar PDF; desktop=arquivos/shell. Para "
            "perguntas de conhecimento geral use null.\n\n"
            "TAREFA: " + query + "\n\n"
            "Responda APENAS JSON valido:\n"
            '{"complexity":"trivial|simple|moderate|complex",'
            '"needs_planning":bool,"needs_reader":bool,"needs_worker":bool,'
            '"iterations":int,"skip_to_reporter":bool,'
            '"worker_agent":"scholar|sql|prism|pdf|desktop|null",'
            '"reasoning":"frase"}'
        )
        try:
            raw = self.client.chat(
                prompt=prompt,
                system=(
                    "Voce e um classificador de pipelines. Responda apenas "
                    "JSON valido. Sem markdown, sem texto extra."
                ),
                model=MODELS.get("autocomplete", MODELS.get("chat")),
                temperature=0.0,
                max_tokens=256,
            )
            if raw and not raw.startswith("[MOCK]"):
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    data = json.loads(m.group(0))
                    # V12: especialista do Worker, validado contra a lista
                    # conhecida (LLM pode alucinar nome) -> None se invalido.
                    _wa = data.get("worker_agent")
                    _wa = str(_wa).strip().lower() if _wa else None
                    if _wa not in _STAGE_WORKER_AGENTS:
                        _wa = None
                    out = {
                        "complexity": str(data.get("complexity", "moderate")).lower(),
                        "needs_planning": bool(data.get("needs_planning", True)),
                        "needs_reader": bool(data.get("needs_reader", True)),
                        "needs_worker": bool(data.get("needs_worker", True)),
                        "iterations": max(1, min(3, int(data.get("iterations", 1)))),
                        "skip_to_reporter": bool(data.get("skip_to_reporter", False)),
                        "worker_agent": _wa,
                        "reasoning": str(data.get("reasoning", ""))[:200],
                    }
                    # V11.2 (2026-06-11): guarda anti-fast-path-raso UNIFICADA
                    # na decisao do LLM orchestrator. O classificador as vezes
                    # marca skip_to_reporter=True para pedidos que o prompt
                    # conciso do fast-path responde de forma rasa. Antes (V11.0)
                    # so cobria DEMONSTRACAO/PROVA; bench 2026-06-11 mostrou
                    # fisica ("Explique ... e suas implicacoes") caindo em
                    # fast-path com q=64, pois EXPLICACAO/PROFUNDIDADE escapava.
                    # Agora _block_fast_path() unifica os dois ramos (LLM e
                    # heuristico). So ESCALA fast-path -> Worker; nunca rebaixa.
                    _fp = _block_fast_path(query) if out.get(
                        "skip_to_reporter") else None
                    if _fp:
                        out["skip_to_reporter"] = False
                        out["needs_worker"] = True
                        out["complexity"] = out.get("complexity") or "moderate"
                        if _fp == "proof":
                            out["iterations"] = max(2, int(out.get("iterations", 1)))
                        out["reasoning"] = (
                            "guarda V11.2 (%s->Worker) | " % _fp
                            + str(out.get("reasoning", "")))[:200]
                    if out["skip_to_reporter"]:
                        out["needs_planning"] = False
                        out["needs_reader"] = False
                        out["needs_worker"] = False
                    out["_source"] = "llm"
                    if cache_key:
                        self._decision_cache_put(cache_key, out)
                    return out
        except Exception as e:
            log.debug("Orchestrator LLM falhou (%s); usando heuristica", e)

        q = (query or "").strip().lower()
        is_simple = any(re.search(p, q) for p in self._SIMPLE_PATTERNS)
        _wants_explanation = any(kw in q for kw in self._EXPLAIN_KW)
        # V10.3 (2026-05-31): heuristica de trivialidade endurecida.
        #  1) pedido de explicacao/aprofundamento -> nunca trivial;
        #  2) padrao simples mas query longa (>=60 chars) -> nao trivial
        #     (multi-part, ex.: "Como funciona X? Cite etapas e enzimas");
        #  3) catch-all de query curta sem acao: so para len < 45 (antes <80,
        #     largo demais -> perguntas explicativas curtas caiam em fast-path).
        if _wants_explanation:
            is_simple = False
        elif is_simple and len(q) >= 60:
            is_simple = False
        elif not is_simple and len(q) < 45 and not any(
                kw in q for kw in ["execute", "rode", "run", "analise",
                                   "compare", "calcule estatist", "plot",
                                   "grafico", "criar", "build", "implementar"]):
            is_simple = True
        if is_simple:
            out = {
                "complexity": "trivial",
                "needs_planning": False,
                "needs_reader": False,
                "needs_worker": False,
                "iterations": 1,
                "skip_to_reporter": True,
                "reasoning": "heuristica: query curta/factual",
                "_source": "heuristic",
            }
            if cache_key:
                self._decision_cache_put(cache_key, out)
            return out
        # V10 (2026-05-30): heuristica cost-aware de iteracoes. Sinais
        # textuais elevam iters ate o teto do perfil (max_iterations).
        _multi_kw = ("compare", "comparar", "contraste", "diferenca entre",
                     "analise e", "implemente e", "rode e", "avalie e",
                     "explore", "investigue", " vs ", " versus ",
                     "review", "revise", "valide e", "iterativ")
        _complex_kw = ("pipeline", "fluxo completo", "design experimental",
                       "machine learning", "deep learning", "molecular dynamics",
                       "simula", "modela", "ajust", "regressao", "curva de")
        n_m = sum(1 for m in _multi_kw if m in q)
        n_c = sum(1 for m in _complex_kw if m in q)
        if n_m >= 2 or (n_m >= 1 and n_c >= 1):
            _hi = 3
        elif n_m >= 1 or n_c >= 1:
            _hi = 2
        else:
            _hi = 1
        try:
            _max_it = int(get_profile_policy().get("max_iterations") or 3)
        except Exception:
            _max_it = 3
        _hi = max(1, min(_hi, _max_it))
        out = {
            "complexity": "complex" if _hi >= 3 else "moderate",
            "needs_planning": True,
            "needs_reader": True,
            "needs_worker": True,
            "iterations": _hi,
            "skip_to_reporter": False,
            "reasoning": (
                "fallback: pipeline (multi=%d complex=%d iters=%d/teto=%d)"
                % (n_m, n_c, _hi, _max_it)
            ),
            "_source": "fallback",
        }
        if cache_key:
            self._decision_cache_put(cache_key, out)
        return out

    def _route_via_llm(self, query):
        domains_doc = (
            "- prism: analise estatistica completa, ANOVA, t-test, "
            "comparar grupos, normalidade, p-value\n"
            "- sql: queries SQL, bancos relacionais, joins, schemas\n"
            "- pdf: sumarizar/extrair conteudo de PDFs cientificos\n"
            "- scholar: buscar/sintetizar artigos PubMed, arXiv, Google Scholar\n"
            "- desktop: operacoes em arquivos locais ou execucao de codigo\n"
            "- gateway: chat geral, duvida factual, explicacao conceitual\n"
            "- none: tarefa generica que precisa de pipeline completo"
        )
        prompt = (
            "Classifique a tarefa abaixo escolhendo UM rotulo dentre: "
            "prism, sql, pdf, scholar, desktop, gateway, none.\n\n"
            "Definicoes:\n" + domains_doc + "\n\n"
            "Tarefa: " + query + "\n\n"
            "Responda APENAS JSON: "
            '{"domain":"<rotulo>","confidence":<0..1>,"reason":"<frase>"}'
        )
        try:
            raw = self.client.chat(
                prompt=prompt,
                system="Classificador. Responda apenas JSON valido.",
                model=MODELS.get("autocomplete", MODELS.get("chat")),
                temperature=0.0,
                max_tokens=128,
            )
            if not raw or raw.startswith("[MOCK]"):
                return None
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return None
            data = json.loads(m.group(0))
            domain = (data.get("domain") or "").strip().lower()
            conf = float(data.get("confidence", 0))
            log.info("LLM router: domain=%s conf=%.2f", domain, conf)
            valid = ("prism", "sql", "pdf", "scholar", "desktop", "gateway")
            if domain in valid and conf >= 0.55:
                return domain
            if domain == "none":
                return "none"
            return None
        except Exception as e:
            log.debug("LLM router falhou (%s); usando heuristica", e)
            return None

    def _delegate_to_specialist(self, query, context):
        try:
            domain = self._route_via_llm(query)
            route_method = "llm"
            if domain in (None, "none"):
                domain = _detect_domain(query)
                route_method = "heuristic"
            if not domain or domain == "none":
                # V8: ultima tentativa via capabilities()
                domain = self._route_via_capabilities(query)
                if domain:
                    route_method = "capabilities"
            # V10.5: blindagem final. O gateway (chat raso) JAMAIS atende query
            # profunda, qualquer que seja a camada que o escolheu (llm/
            # heuristic/capabilities). Corrige regressao da V10.4: _detect_domain
            # ja rebaixava gateway->None, mas _route_via_capabilities reinjetava
            # 'gateway' para historia/fisica -> delegacao rasa (qualidade 25/28).
            # Agora caem no pipeline completo, como os demais dominios.
            if domain == "gateway" and _is_deep_query(query):
                log.info("V10.5: query profunda -> pipeline (gateway rebaixado)")
                return None
            if not domain or domain == "none":
                return None
            from lilo import _load_agents
            agents = _load_agents()
            if domain not in agents:
                log.info("Dominio %s detectado mas agente nao carregado", domain)
                return None
            log.info("Villa -> delegando a '%s' (router=%s)", domain, route_method)
            try:
                from shared.cost_tracker import get_tracker
                get_tracker().log_request(
                    backend="villa_route", model=route_method,
                    subagent=domain, tier="route_decision",
                    query_preview=query[:80],
                )
            except Exception:
                pass
            result = agents[domain].run(query, dict(context or {}))
            if not result or "[ERRO" in result or len(result.strip()) < 40:
                log.info("Resultado fraco do especialista; pipeline normal")
                return None
            return {"agent": domain, "result": result, "route_method": route_method}
        except Exception as e:
            log.warning("Falha na delegacao: %s", e)
            return None

    def _call_agent(self, role, prompt, tier=None):
        """Executa um estagio do pipeline com fallback automatico.

        V2 (2026-05-12): registra telemetria stage-level no cost_tracker.
        """
        model = VILLA_MODELS.get(role, VILLA_MODELS["worker"])
        # V10.9: worker/reader usam modelo instruct GERAL para dominios de
        # conhecimento; o coder (qwen) so e mantido quando a query original
        # teve intencao de codigo (self._cur_code_intent, setado no pipeline).
        if role in ("worker", "reader") and not getattr(
                self, "_cur_code_intent", False):
            model = VILLA_WORKER_GENERAL_MODEL
        effective_tier = tier or DEFAULT_STAGE_TIERS.get(role, "ollama")
        system = EXPERT_SYSTEM.format(role=role)
        last_error = None
        result_text = None
        backend_label = "ollama"
        stage_t0 = time.time()
        # V9 (2026-05-22): circuit breaker -- contra backend mock/indisponivel
        # nao adianta repetir nem dormir RETRY_DELAY. Reduz os ~5s/stage de
        # lentidao observados em modo degradado (secao 4.3 do relat. 2026-05-20).
        # V9.4 (2026-05-30): estender circuito aberto p/ ModuleNotFoundError
        # ("anthropic", "ollama"). Antes, quando o backend reportado era
        # "anthropic" mas o pkg nao estava instalado, o pipeline ainda fazia
        # MAX_RETRIES x RETRY_DELAY = ~3s/stage perdidos. Agora flagamos
        # _circuit_open na primeira ImportError e o resto da chamada/stage
        # nao reintenta nem dorme. Reduz pipeline moderate iters=2 de
        # ~7.7s para ~2.5s em modo degradado.
        try:
            _backend = self.client.backend
        except Exception:
            _backend = "unknown"
        _circuit_open = (_backend == "mock")
        # V11.2 (2026-06-11): erro de PAYLOAD (HTTP 400) e determinístico --
        # reintentar com o MESMO payload ou cair no fallback de modelo (que
        # reusa o payload) so gasta tempo. Foi o que custou ~3-5s/stage no
        # bench 2026-06-11 (keep_alive=-1 -> 400 em planner+fallback+worker,
        # identicos). Quando setado, pula retry E fallback. Distingue-se de
        # 404 (modelo inexistente), onde o fallback de modelo AINDA ajuda.
        _payload_error = False
        effective_retries = 1 if _circuit_open else MAX_RETRIES
        # V11.3 (2026-06-11): temperatura por papel E por intencao. O bench com
        # JUIZ LLM (quality_judge) revelou que o Worker em queries de
        # CONHECIMENTO factual tinha variancia altissima de correcao (mesma
        # pergunta de biologia: ora 86, ora 10 -- invencoes factuais
        # intermitentes), invisivel ao _quality_score heuristico. temp=0.4
        # alimenta essa invencao. Para conhecimento (nao-codigo) baixamos o
        # Worker para 0.25 (factualidade > criatividade); codigo e planner
        # seguem em 0.4 (onde alguma exploracao ajuda). HIPOTESE a validar com
        # N>=5 corridas + juiz (ver relatorio 2026-06-11).
        if role == "worker" and not getattr(self, "_cur_code_intent", False):
            _temp = 0.25
        elif role in ("worker", "planner"):
            _temp = 0.4
        else:
            _temp = 0.3
        for attempt in range(1, effective_retries + 1):
            try:
                log.info("    %s (%s, tier=%s, temp=%.2f) tentativa %d/%d",
                         role, model, tier or "auto", _temp, attempt, effective_retries)
                result = self.client.chat(
                    prompt=prompt, system=system, model=model,
                    temperature=_temp,
                    max_tokens=4096, tier=tier,
                )
                if result and not result.startswith("[MOCK]"):
                    result_text = result
                    break
                last_error = "resposta vazia ou mock"
                if _circuit_open:
                    break  # circuito aberto: nao reintentar
            except ModuleNotFoundError as e:
                last_error = "pacote ausente: %s" % e
                log.warning("    %s ModuleNotFoundError: %s -- abrindo circuito",
                            role, e)
                _circuit_open = True
                try:
                    self.client._backend = "mock"
                except Exception:
                    pass
                break
            except Exception as e:
                last_error = str(e)
                # V11.2: status HTTP via e.response.status_code (requests.
                # HTTPError) sem importar requests. 4xx != 5xx no remedio.
                _status = getattr(getattr(e, "response", None),
                                  "status_code", None)
                if _status == 400:
                    _payload_error = True
                    log.error("    %s erro 400 (payload invalido) -- "
                              "sem retry/fallback: %s", role, e)
                    break
                if _status is not None and 400 <= _status < 500:
                    # outros 4xx (ex.: 404 modelo inexistente): nao reintentar
                    # o mesmo modelo, mas permitir o fallback de modelo abaixo.
                    log.warning("    %s erro %s -- sem retry (tenta fallback)",
                                role, _status)
                    break
                log.warning("    %s tentativa %d falhou: %s", role, attempt, e)
                if attempt < effective_retries:
                    log.info("    Retry em %.1fs...", RETRY_DELAY)
                    time.sleep(RETRY_DELAY)
        if result_text is None:
            fallback_model = MODELS.get("chat", "llama3.1:8b-instruct-q8_0")
            if fallback_model != model and not _circuit_open and not _payload_error:
                try:
                    log.info("    Fallback: %s -> %s", role, fallback_model)
                    fb = self.client.chat(
                        prompt=prompt, system=system,
                        model=fallback_model, temperature=0.3, max_tokens=4096)
                    # V9: rejeitar mock tambem no fallback (antes vazava "[MOCK]")
                    if fb and not fb.startswith("[MOCK]"):
                        result_text = fb
                        model = fallback_model
                        backend_label = "ollama_fallback"
                    else:
                        last_error = "fallback retornou vazio/mock"
                except Exception as e2:
                    log.error("    Fallback tambem falhou: %s", e2)
                    last_error = str(e2)
        # V9 (2026-05-22): escalonamento p/ nuvem (proposta 6.2) -- gated DUPLO:
        # env LILO_ALLOW_CLOUD_FALLBACK=1 E policy allow_cloud do perfil de
        # servidor. Default OFF: nunca gasta sem o usuario optar E sem o perfil
        # permitir. Realiza "de acordo com o setup do servidor".
        if result_text is None:
            _policy = get_profile_policy()
            _env_ok = _os.getenv("LILO_ALLOW_CLOUD_FALLBACK", "0") == "1"
            if _env_ok and _policy.get("allow_cloud"):
                try:
                    log.warning("    Escalando stage %s -> claude_sonnet "
                                "(local falhou; perfil '%s' permite nuvem)",
                                role, _policy.get("profile"))
                    cloud = self.client.chat(
                        prompt=prompt, system=system,
                        tier="claude_sonnet", max_tokens=4096)
                    if cloud and not cloud.startswith("[MOCK]"):
                        result_text = cloud
                        model = "claude_sonnet"
                        backend_label = "claude_sonnet"
                except Exception as e3:
                    log.error("    Escalonamento nuvem falhou: %s", e3)
                    last_error = str(e3)

        duration_ms = int((time.time() - stage_t0) * 1000)
        try:
            from shared.cost_tracker import get_tracker
            if (effective_tier or "").startswith("claude"):
                backend_label = effective_tier
            get_tracker().log_request(
                backend=backend_label, model=model,
                subagent="villa_%s" % role, tier=effective_tier,
                query_preview=("[%s] %s" % (role, prompt))[:80],
                duration_ms=duration_ms,
            )
        except Exception as _tex:
            log.debug("V2 telemetria stage falhou: %s", _tex)

        if result_text is not None:
            return result_text
        # V10.7 (2026-06-06): reportar o numero REAL de tentativas. Com o
        # circuit breaker aberto (backend mock) effective_retries=1, mas a
        # mensagem antiga imprimia MAX_RETRIES (=2), gerando o log enganoso
        # "falhou apos 2 tentativas" quando so houve 1 chamada. Ver bench 06-06.
        log.error("  Agente %s falhou apos %d tentativa(s): %s",
                  role, effective_retries, last_error)
        return "[%s ERRO apos %d tentativas: %s]" % (role, effective_retries, last_error)

    def route_target(self, query, available=None):
        """V12 (2026-06-11): PORTA ÚNICA de roteamento semântico.

        Decide QUAL subagente deve assumir a query, reusando a mesma cascata
        do _delegate_to_specialist (LLM router -> heurística de domínio ->
        capabilities). Substitui o keyword-router raso de lilo._detect_tab.

        Retorna (target, method):
          - target: nome de um subagente especialista (sql/pdf/scholar/prism/
            desktop/gateway) quando há domínio claro; senão "villa" (pipeline
            multi-agente para tarefas complexas/ambíguas).
          - method: "llm" | "heuristic" | "capabilities" | "deep" | "ambiguous".

        `available`: conjunto de nomes de subagentes carregados (opcional);
        se um domínio detectado não estiver disponível, cai em "villa".
        """
        domain = self._route_via_llm(query)
        method = "llm"
        if domain in (None, "none"):
            domain = _detect_domain(query)
            method = "heuristic"
        if not domain or domain == "none":
            domain = self._route_via_capabilities(query)
            method = "capabilities"
        # Gateway é chat raso: nunca atende query profunda -> pipeline completo.
        if domain == "gateway" and _is_deep_query(query):
            return "villa", "deep"
        # Sem domínio claro -> pipeline multi-agente (não o gateway raso).
        if not domain or domain == "none":
            return "villa", "ambiguous"
        if available and domain not in available:
            return "villa", method
        return domain, method

    def explain_routing(self, query, allow_delegate=True):
        """V7 (2026-05-12): retorna a decisao de roteamento sem executar pipeline."""
        domain = _detect_domain(query)
        delegate_target = domain if (domain and domain != "none"
                                     and allow_delegate) else None
        try:
            decision = self._orchestrate_decision(query)
        except Exception as e:
            decision = {
                "complexity": "unknown",
                "needs_planning": True,
                "needs_reader": True,
                "needs_worker": True,
                "iterations": 1,
                "skip_to_reporter": False,
                "reasoning": "explain_routing: _orchestrate_decision falhou (%s)" % e,
                "_source": "error",
            }
        stages = ["orchestrator"]
        if not decision.get("skip_to_reporter"):
            if decision.get("needs_planning", True):
                stages.append("planner")
            if decision.get("needs_reader", True):
                stages.append("reader")
            if decision.get("needs_worker", True):
                stages.append("worker")
        stages.append("reporter")
        return {
            "query": query,
            "domain_heuristic": domain,
            "delegate_target": delegate_target,
            "decision": decision,
            "stages_planned": stages,
            "stage_tiers": dict(DEFAULT_STAGE_TIERS),
            "cache": self.cache_stats(),
            "domains_supported": sorted(get_domain_keywords().keys()),
            "server_profile": get_profile_policy(),  # V9 2026-05-22
        }

    def get_tools(self):
        return [
            {
                "name": "villa_pipeline",
                "description": (
                    "Pipeline completo Villa Lobos com smart routing: "
                    "Orchestrator emite JSON declarando quais stages executar."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Tarefa"},
                        "iterations": {"type": "integer", "default": 1},
                        "use_reader": {"type": "boolean", "default": True},
                        "base_path": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "villa_quick_ask",
                "description": "Pergunta rapida a um agente Villa Lobos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "agent": {
                            "type": "string",
                            "enum": ["orchestrator", "planner", "reader",
                                     "worker", "reporter"],
                            "default": "worker",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "villa_explain_routing",
                "description": (
                    "Debug: descreve o roteamento que Villa_Lobos faria "
                    "para a query (decisao do Orchestrator + delegate + "
                    "stages + tiers + stats de cache) SEM executar pipeline. "
                    "Util para tracing e validar mudancas em domains.yaml."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Tarefa"},
                        "allow_delegate": {"type": "boolean", "default": True},
                    },
                    "required": ["query"],
                },
            },
        ]

    def health(self):
        h = self.client.health()
        return {
            "status": "ok" if h.get("backend") != "mock" else "degraded",
            "backend": h.get("backend"),
            "models": VILLA_MODELS,
            "domains_supported": list(get_domain_keywords().keys()) + ["none"],
            "domains_source": "yaml" if _DOMAINS_CACHE.get("mtime") else "defaults",
            "default_tiers": DEFAULT_STAGE_TIERS,
            "smart_routing": True,
            "delegation_enabled": True,
            "decision_cache": self.cache_stats(),
        }

    def capability_registry(self):
        """Coleta o manifesto capabilities() de todos os subagentes carregados.

        Retorna dict { agent_name: capabilities_dict }. Usado para roteamento
        explainable (vs. keyword matching duro) e para lilo_server_profile.
        """
        registry = {}
        try:
            from lilo import _load_agents
            agents = _load_agents()
        except Exception as e:
            log.warning("capability_registry: falha ao carregar agentes (%s)", e)
            return registry
        for name, agent in agents.items():
            try:
                cap = agent.capabilities() if hasattr(agent, "capabilities") else {}
            except Exception as e:
                cap = {"error": str(e)}
            registry[name] = cap
        return registry

    def _route_via_capabilities(self, query):
        """Roteia via capabilities() consultando o manifesto de cada agente.

        Pontuacao = soma de matches de keywords (case-insensitive). Retorna o
        agente com maior pontuacao ou None se nenhum encaixou.
        """
        ql = (query or "").lower()
        best = (None, 0)
        for name, cap in self.capability_registry().items():
            if name == "villa":
                continue
            score = 0
            for kw in (cap.get("keywords", []) or []):
                if not kw:
                    continue
                # V10.6 (2026-06-05): match por FRONTEIRA DE PALAVRA, nao
                # substring. Bug corrigido: o keyword 'cat' do agente desktop
                # casava dentro de "CATalise" (quimica) e sequestrava a query
                # profunda para um `fs_list`. Keywords multi-palavra (ex.:
                # "criar arquivo") seguem casando como frase. \b e unicode-aware
                # para str em Python 3, entao acentos contam como word-char.
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", ql):
                    score += 1
            if score > best[1]:
                best = (name, score)
        if best[1] > 0:
            return best[0]
        return None

    def capabilities(self):
        """Manifesto V8 do orquestrador Villa_Lobos."""
        return {
            "domain": "villa",
            "keywords": ["orquestrar", "pipeline", "multi-agente", "plan-read-work", "complex", "compare", "investigate", "deep analysis"],
            "tools": [t["name"] for t in self.get_tools()],
            "cost_tier": "claude_sonnet",
            "local_only": False,
            "description": "Orquestrador multi-stage com smart routing e delegacao a especialistas.",
            "stages": ["orchestrator", "planner", "reader", "worker", "reporter"],
            "domains_supported": sorted(get_domain_keywords().keys()),
        }
