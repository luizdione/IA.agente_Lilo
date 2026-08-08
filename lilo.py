"""
lilo.py -- Orquestrador Central LILO
=====================================
Ponto de entrada unico que roteia queries para os 7 subagentes ativos:
  - sql     -> Analise_SQL/agent.py     (SQL + estatistica)
  - pdf     -> PDFs_library/agent.py    (sumarizacao de PDFs)
  - scholar -> scholaragent/agent.py    (busca academica: PubMed/arXiv/Scholar)
  - prism   -> prism_ai/                (estatistica + grafico cientifico)
  - villa   -> villa_lobos/             (orquestrador 5-stage: plan/read/work/report)
  - gateway -> gateway/                 (chat geral / fallback LLM)
  - desktop -> desktop/                 (operacoes locais de arquivo, allow-list)

Uso CLI:
    python lilo.py "liste as tabelas disponiveis"
    python lilo.py sql "SELECT COUNT(*) FROM genomas"
    python lilo.py pdf "resumir artigo" --file paper.pdf --mode introduction
    python lilo.py scholar "inibidores de TcTR em bovinos"
    python lilo.py prism "compare grupos A e B com t-test"
    python lilo.py villa "rodar pipeline completo no projeto X"
    python lilo.py health

Uso como modulo:
    from lilo import route
    resposta = route("buscar artigos sobre docking molecular")
"""

import sys
import os
import argparse
from pathlib import Path

# Garante que o projeto esta no path
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.logger import get_logger
from shared.utils import load_env

load_env()
log = get_logger("LILO")

# -- Carregamento lazy dos subagentes ----------------------------------------
_agents: dict = {}


def _load_agents() -> dict:
    """Inicializa os subagentes (lazy -- so carrega quando necessario)."""
    if _agents:
        return _agents

    log.info("Inicializando subagentes LILO...")

    _AGENT_REGISTRY = [
        ("sql",     "agents.Analise_SQL.agent",  "SQLAgent"),
        ("pdf",     "agents.PDFs_library.agent",  "PDFAgent"),
        ("scholar", "agents.scholaragent.agent",  "ScholarAgent"),
        ("prism",   "agents.prism_ai",            "PrismAgent"),
        ("villa",   "agents.villa_lobos",         "VillaLobosAgent"),
        ("gateway", "agents.gateway",             "GatewayAgent"),
        ("desktop", "agents.desktop",             "DesktopAgent"),
        ("paper",   "agents.paper.agent",         "PaperAgent"),
        ("docgen",  "agents.docgen.agent",        "DocGenAgent"),
        ("skillsmith", "agents.skillsmith.agent",  "SkillSmithAgent"),
    ]

    for name, module_path, class_name in _AGENT_REGISTRY:
        try:
            mod = __import__(module_path, fromlist=[class_name])
            _agents[name] = getattr(mod, class_name)()
            log.info(f"  ok {class_name}")
        except Exception as e:
            log.warning(f"  x {class_name} nao disponivel: {e}")

    log.info(f"Subagentes carregados: {list(_agents.keys())}")
    return _agents


# -- Roteamento ---------------------------------------------------------------

_KEYWORD_MAP = {
    "sql":     ["sql", "query", "select", "tabela", "banco", "database",
                "sqlite", "mysql", "estatistica", "anova", "t-test"],
    "pdf":     ["pdf", "artigo", "paper", "documento", "arquivo",
                "resumir", "sumarizar", "introducao", "metodos", "doi"],
    "scholar": ["pubmed", "arxiv", "scholar", "literatura", "referencia",
                "papers", "publicacoes", "buscar artigos", "pesquisa academica"],
    "prism":   ["prism", "analise estatistica", "teste estatistico", "boxplot",
                "anova", "t-test", "mann-whitney", "kruskal", "shapiro",
                "grafico cientifico", "publicacao", "pzfx", "graphpad",
                "comparar grupos", "normalidade", "p-value", "p-valor",
                "experimento", "dados experimentais"],
    "villa":   ["villa", "pipeline completo", "planejar e executar",
                "ler e executar", "projeto completo", "orquestrar",
                "multi-step", "etapas", "plan and execute"],
    # paper: redacao cientifica (keywords ESPECIFICAS p/ nao capturar leitura
    # de PDF -> que vai ao 'pdf'). "escrever/redigir/montar o paper", manuscrito.
    "paper":   ["escrever o paper", "escrever paper", "redigir o manuscrito",
                "redigir manuscrito", "montar o artigo", "redacao cientifica",
                "build_paper", "manuscrito", "responder revisores",
                "preparar o artigo para", "submissao", "redigir a introducao",
                "redigir a discussao", "escrever o abstract"],
    # docgen: documentos de escritorio (relatorio/planilha/slides).
    "docgen":  ["gerar documento", "criar documento", "relatorio word", "docx",
                "planilha", "xlsx", "excel", "apresentacao", "slides", "pptx",
                "powerpoint", "gerar relatorio", "exportar para word"],
    "skillsmith": ["criar agente", "novo subagente", "criar skill", "nova skill",
                   "scaffold", "gerar agente", "skill creator", "criar capacidade"],
}


def _detect_tab(query: str):
    """Detecta automaticamente o subagente mais adequado para a query."""
    q = query.lower()
    scores = {tab: 0 for tab in _KEYWORD_MAP}
    for tab, keywords in _KEYWORD_MAP.items():
        for kw in keywords:
            if kw in q:
                scores[tab] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def route(query, tab=None, context=None):
    """
    Roteia a query para o subagente correto.

    Args:
        query   -- pergunta ou comando do usuario
        tab     -- subagente explicito ("sql" | "pdf" | "scholar" | "gateway")
                   Se None, deteccao automatica por palavras-chave.
        context -- dict com informacoes adicionais (file_path, mode, db_path, etc.)

    Returns:
        Resposta em texto/Markdown do subagente.
    """
    import time
    from shared.policy import get_policy_engine, ExecutionTier
    from shared.cost_tracker import get_tracker

    agents = _load_agents()
    ctx    = context or {}
    orig_query = query  # preservado p/ telemetria (preview sem o contexto injetado)
    policy = get_policy_engine()
    tracker = get_tracker()

    detected = tab
    route_method = "explicit" if tab else None
    if not detected:
        # V12 (2026-06-11): roteador SEMÂNTICO como porta única. Em modo auto,
        # o Villa decide qual subagente assume a query (LLM router -> heurística
        # -> capabilities), substituindo o keyword-router raso (_detect_tab).
        # Domínio claro -> especialista direto; ambíguo/complexo -> "villa"
        # (pipeline multi-agente). Keyword-router vira fallback se o Villa não
        # estiver disponível ou falhar. Desligável via LILO_SEMANTIC_ROUTER=0.
        if os.getenv("LILO_SEMANTIC_ROUTER", "1") == "1" and "villa" in agents:
            try:
                detected, route_method = agents["villa"].route_target(
                    query, set(agents))
                # Se a porta única decidiu "villa", é tarefa de pipeline:
                # o Villa roda direto, sem re-delegar (evita dupla decisão).
                if detected == "villa":
                    ctx.setdefault("allow_delegate", False)
                log.info("Roteador semantico -> %s (via %s)",
                         detected, route_method)
            except Exception as e:
                log.warning("Roteador semantico falhou (%s); usando keyword", e)
                detected = _detect_tab(query)
                route_method = "keyword_fallback"
        else:
            detected = _detect_tab(query)
            route_method = "keyword"

    decision = policy.decide(query, context=ctx, subagent=detected or "gateway")
    log.info(f"Policy -> tier={decision.tier.value} | model={decision.model} | reason={decision.reason}")

    # No-LLM: executar direto sem modelo
    if decision.tier == ExecutionTier.NO_LLM:
        ctx["_direct_query"] = True
        ctx["_tier"] = decision.tier.value
        target = detected if detected and detected in agents else "gateway"
        if target in agents:
            t0 = time.time()
            result = agents[target].run(query, ctx)
            tracker.log_request("no_llm", "none", subagent=target, tier=decision.tier.value,
                                query_preview=query[:80], duration_ms=int((time.time()-t0)*1000))
            return result

    # Executar com o tier decidido
    ctx["_tier"] = decision.tier.value
    ctx["_model"] = decision.model
    target = detected if detected and detected in agents else "gateway"

    if target not in agents:
        if "gateway" in agents:
            target = "gateway"
        else:
            return "[LILO] Nenhum subagente disponivel. Verifique se Ollama esta rodando."

    log.info(f"Roteamento -> {target} | tier={decision.tier.value}")

    # Auto-consulta de notas do projeto (Task 4): se o dashboard injetou
    # 'project_notes' no contexto, prefixamos a query com elas para que o
    # LLM tenha consciencia das etapas concluidas, pendentes e historico
    # antes de responder. Aplica a TODOS os subagentes sem precisar mudar
    # cada um individualmente.
    # V15 FASE 3: memoria persistente do DONO. Revive ctx['owner_verified']
    # (antes MORTO: o dashboard setava a flag mas ninguem a lia). So quando a
    # voz/sessao do dono foi verificada; busca curada em ns='user', top-k
    # pequeno (a busca LIKE e fraca -> limita ruido). Marcada como DADO, nao
    # instrucao (defesa anti prompt-injection, correcao #4 da revisao).
    # V18.4 E3: inject unificado via memory_facade — SEMANTICO desde o E2
    # (com fallback textual transparente). Mantem a politica V15 intacta:
    # memoria do dono SO com owner_verified; bloco marcado como DADO, nao
    # instrucao (anti prompt-injection).
    try:
        from shared.memory_facade import get_relevant_context
        mem_bloco = get_relevant_context(
            query, project_id=ctx.get("project_id"),
            owner_verified=bool(ctx.get("owner_verified")), k=5)
        if mem_bloco:
            query = mem_bloco + "\n\n" + query
            log.info("Memoria relevante injetada (%d chars)", len(mem_bloco))
    except Exception as e:
        log.debug("memory_facade inject falhou: %s", e)

    notes = ctx.get("project_notes")
    if notes:
        query = (
            "[Contexto do projeto - notas auto-mantidas pelo LILO]\n"
            f"{notes}\n"
            "[Fim do contexto]\n\n"
            f"Pergunta atual: {query}"
        )
        log.info(f"Notas do projeto injetadas ({len(notes)} chars)")

    # Historico de conversa multi-turno (Fase plataforma hibrida, 2026-05-25).
    # Clientes com sessao -- ex.: a API HTTP em /v1/chat com session_id --
    # passam o historico ja formatado em ctx["conversation_history"]. route()
    # permanece stateless: aqui apenas prefixamos os turnos anteriores para
    # dar memoria de conversa (estilo Claude Desktop) sem mudar cada subagente.
    conv = ctx.get("conversation_history")
    if conv:
        query = (
            "[Historico da conversa - turnos anteriores desta sessao]\n"
            f"{conv}\n"
            "[Fim do historico]\n\n"
            f"Mensagem atual do usuario: {query}"
        )
        log.info(f"Historico de conversa injetado ({len(conv)} chars)")

    # Sintese de diretorio anexado (Task 2): se o dashboard injetou
    # 'dir_synthesis', incluimos no contexto antes da pergunta. Isso da ao
    # LLM o conhecimento da estrutura/etapas/TODOs do projeto sem o usuario
    # precisar repetir.
    dir_synth = ctx.get("dir_synthesis")
    if dir_synth:
        query = (
            "[Sintese de diretorio anexado - gerada offline pelo LILO]\n"
            f"{dir_synth}\n"
            "[Fim da sintese]\n\n"
            f"{query}"
        )
        log.info(f"Sintese de diretorio injetada ({len(dir_synth)} chars)")

    t0 = time.time()
    try:
        result = agents[target].run(query, ctx)
    except Exception as e:
        next_tier = policy.get_fallback(decision.tier)
        if next_tier != decision.tier:
            log.warning(f"Fallback: {decision.tier.value} -> {next_tier.value} (erro: {e})")
            ctx["_tier"] = next_tier.value
            from shared.policy import TIER_MODELS
            ctx["_model"] = TIER_MODELS.get(next_tier)
            result = agents[target].run(query, ctx)
        else:
            result = f"[LILO] Erro: {e}"

    duration = int((time.time() - t0) * 1000)
    # V18 QW4: para tiers claude_* o custo REAL (usage da resposta) e gravado
    # pelo llm_client (backend="anthropic"); registrar TAMBEM a estimativa aqui
    # dupla-contaria o gasto do dia -- e registrava custo fantasma quando o
    # agente nem chamava a Anthropic (a decisao da policy nao e consumida
    # pelos agentes, ver QW2). Zeramos o custo estimado neste registro; ele
    # segue vivo no fallback em-processo (record_cost), usado apenas quando a
    # telemetria SQLite esta desabilitada.
    logged_cost = (0.0 if decision.tier.value.startswith("claude")
                   else decision.estimated_cost)
    tracker.log_request(
        backend=decision.tier.value,
        model=decision.model or "",
        subagent=target,
        tier=decision.tier.value,
        cost_usd=logged_cost,
        query_preview=orig_query[:80],
        duration_ms=duration,
    )
    policy.record_cost(decision.estimated_cost)

    return result


def health_check():
    """Verifica status de todos os subagentes e backends.

    Inclui no topo o backend LLM ativo (litellm | ollama | anthropic | mock)
    para facilitar diagnostico rapido em scripts e CI.
    """
    agents = _load_agents()
    lines = ["## LILO -- Status dos Subagentes\n"]

    # Backend LLM ativo (resolve via shared.llm_client sem instanciar agente extra)
    try:
        from shared.llm_client import LLMClient
        backend_info = LLMClient().health()
        backend = backend_info.get("backend", "?")
        extras = []
        if backend == "ollama":
            extras.append(backend_info.get("ollama_url", ""))
        elif backend == "litellm":
            extras.append(backend_info.get("litellm_url", ""))
        elif backend == "anthropic":
            extras.append("api-key configurada" if backend_info.get("anthropic_configured") else "sem chave")
        extras.append(f"model={backend_info.get('default_model','?')}")
        lines.append(f"**LLM backend**: {backend} ({' | '.join(x for x in extras if x)})")
    except Exception as e:
        lines.append(f"**LLM backend**: indisponivel ({e})")

    lines.append("")  # separador visual

    for name, agent in agents.items():
        try:
            status = agent.health()
            lines.append(f"ok **{name}**: {status.get('status', 'ok')}")
        except Exception as e:
            lines.append(f"FAIL **{name}**: {e}")

    if not agents:
        lines.append("FAIL Nenhum subagente carregado.")

    return "\n".join(lines)


# -- API centralizada para MCPs -----------------------------------------------

def get_tool_map():
    """
    Mapa centralizado tool_name -> (tab, context_builder).
    Todos os MCPs (lilo_mcp, lilo_serve, lilo_api) devem usar este mapa.
    """
    return {
        # SQL
        "sql_query":          ("sql",     lambda a: {"db_path": a.get("db_path",""), "table": a.get("table","")}),
        "sql_stats":          ("sql",     lambda a: {"table": a.get("table","")}),
        # PDF
        "pdf_summarize":      ("pdf",     lambda a: {"file_path": a.get("file_path",""), "mode": a.get("mode","simple")}),
        "pdf_search":         ("pdf",     lambda a: {}),
        "pdf_list":           ("pdf",     lambda a: {}),
        # Scholar
        "scholar_search":     ("scholar", lambda a: {"source": a.get("source","auto"), "max_results": a.get("max_results",5), "synthesize": False}),
        "scholar_synthesize": ("scholar", lambda a: {"max_results": a.get("max_results",5), "synthesize": True}),
        "scholar_review":     ("scholar", lambda a: {"mode": "review", "max_results": a.get("max_results",20)}),
        # Paper (redacao cientifica -- skill build_paper)
        "paper_outline":      ("paper",   lambda a: {"mode": "outline", "journal": a.get("journal","")}),
        "paper_section":      ("paper",   lambda a: {"mode": "section", "section": a.get("section","introducao"), "journal": a.get("journal",""), "k": a.get("k",8)}),
        "paper_references":   ("paper",   lambda a: {"mode": "references", "k": a.get("k",8)}),
        "paper_draft":        ("paper",   lambda a: {"mode": "draft", "journal": a.get("journal",""), "k": a.get("k",10)}),
        # root vazio -> deixa o agente usar seu default (PAPER_out); nao sobrescreve.
        "paper_build":        ("paper",   lambda a: {"mode": "build", **({"root": a["root"]} if a.get("root") else {})}),
        # docgen
        "make_report_docx":   ("docgen",  lambda a: {"mode": "report", "name": a.get("name",""), "data": a.get("data","")}),
        "make_docx":          ("docgen",  lambda a: {"mode": "docx", "content": a.get("content",""), "name": a.get("name","")}),
        "make_xlsx":          ("docgen",  lambda a: {"mode": "xlsx", "csv_path": a.get("csv_path",""), "tsv": a.get("tsv",""), "csv": a.get("csv",""), "name": a.get("name","")}),
        "make_pptx":          ("docgen",  lambda a: {"mode": "pptx", "outline": a.get("outline",""), "name": a.get("name","")}),
        # skillsmith (criador de subagentes)
        "propose_agent":      ("skillsmith", lambda a: {"description": a.get("query","")}),
        "create_agent_scaffold": ("skillsmith", lambda a: {"name": a.get("name",""), "description": a.get("description",""), "keywords": a.get("keywords"), "tools": a.get("tools")}),
        # Prism AI
        "prism_analyze":      ("prism",  lambda a: {"file_path": a.get("file_path",""), "output_dir": a.get("output_dir",""), "language": a.get("language","en"), "alpha": a.get("alpha",0.05)}),
        "prism_classify":     ("prism",  lambda a: {"file_path": a.get("file_path","")}),
        "prism_audit":        ("prism",  lambda a: {"file_path": a.get("file_path",""), "claimed_test": a.get("claimed_test","")}),
        "prism_eda":          ("prism",  lambda a: {"mode": "eda", "file_path": a.get("file_path",""), "output_dir": a.get("output_dir","")}),
        # Villa Lobos
        "villa_pipeline":     ("villa",  lambda a: {"iterations": a.get("iterations",1), "use_reader": a.get("use_reader",True), "base_path": a.get("base_path",".")}),
        "villa_quick_ask":    ("villa",  lambda a: {"agent": a.get("agent","worker")}),
        # V7 (2026-05-12): explain_routing -- debug do roteamento sem rodar pipeline
        "villa_explain_routing": ("villa", lambda a: {"_explain_routing": True, "allow_delegate": a.get("allow_delegate", True)}),
        # Gateway
        "lilo_chat":          ("gateway", lambda a: {"mode": a.get("mode","chat"), "model": a.get("model",None)}),
        "lilo_models":        ("gateway", lambda a: {"_list_models": True}),
        # Health
        "lilo_health":        (None,      None),
    }


def list_all_tools():
    """Agrega tools de todos os subagentes carregados + skills geradas."""
    agents = _load_agents()
    tools = []
    for agent in agents.values():
        try:
            tools.extend(agent.get_tools())
        except Exception as e:
            log.warning(f"Erro ao listar tools de {agent.name}: {e}")
    tools.append({
        "name": "lilo_health",
        "description": "Verifica status de todos os subagentes e backends LLM do LILO.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    })
    # Web search tools
    tools.append({
        "name": "web_search",
        "description": "Busca na internet via DuckDuckGo. Retorna resultados de sites confiaveis (PubMed, arXiv, Nature, Wikipedia, GitHub, etc).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termos de busca"},
                "max_results": {"type": "integer", "description": "Max resultados (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    })
    tools.append({
        "name": "web_fetch",
        "description": "Busca conteudo de uma URL (apenas dominios confiaveis).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL para buscar"},
                "max_chars": {"type": "integer", "description": "Max caracteres (default 5000)", "default": 5000},
            },
            "required": ["url"],
        },
    })

    # Memoria persistente (KV SQLite, sobrevive entre sessoes)
    tools.extend([
        {
            "name": "lilo_memory_set",
            "description": "Salva valor na memoria persistente do LILO (KV SQLite com TTL opcional, sobrevive entre sessoes).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Chave unica dentro do namespace"},
                    "value": {"type": "string", "description": "Valor (string ou JSON)"},
                    "namespace": {"type": "string", "description": "Categoria (default, user, project, cache)", "default": "default"},
                    "tags": {"type": "string", "description": "Tags separadas por virgula", "default": ""},
                    "ttl_seconds": {"type": "integer", "description": "Expira apos N segundos (omita para nao expirar)", "minimum": 0},
                },
                "required": ["key", "value"],
            },
        },
        {
            "name": "lilo_memory_get",
            "description": "Le valor da memoria persistente. Retorna vazio se chave expirou.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string", "default": "default"},
                },
                "required": ["key"],
            },
        },
        {
            "name": "lilo_memory_list",
            "description": "Lista entradas da memoria persistente (filtros opcionais por namespace e tag).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "default": ""},
                    "tag": {"type": "string", "default": ""},
                },
            },
        },
        {
            "name": "lilo_memory_delete",
            "description": "Remove entrada da memoria persistente.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string", "default": "default"},
                },
                "required": ["key"],
            },
        },
        {
            "name": "git_status",
            "description": "Estado da arvore git (branch + arquivos modificados). Somente leitura. (V18.7 E7)",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "git_diff",
            "description": "Diff da arvore git (ou staged com staged=true). Somente leitura, truncado. (V18.7 E7)",
            "inputSchema": {
                "type": "object",
                "properties": {"staged": {"type": "boolean", "default": False}},
            },
        },
        {
            "name": "git_commit",
            "description": "Cria um commit (gate git_write; a chamada explicita autoriza, salvo modo plan). add_all=true por padrao. (V18.7 E7)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "add_all": {"type": "boolean", "default": True},
                },
                "required": ["message"],
            },
        },
        {
            "name": "dev_workflow",
            "description": "Fluxo dev opt-in (LILO_DEV_WORKFLOW=1): testa -> commita -> documenta -> memoriza. Aborta se testes vermelhos. (V18.7 E7)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "test_target": {"type": "string", "default": ""},
                    "project_id": {"type": "string", "default": ""},
                },
                "required": ["message"],
            },
        },
        {
            "name": "mcp_list_servers",
            "description": "Lista servidores MCP externos declarados em config/mcp/clients.yaml e seu estado (V18.6 E6). Nao conecta em nada.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "mcp_list_tools",
            "description": "Lista as tools reais de um servidor MCP externo (conecta uma vez). Sujeito a allow-list.",
            "inputSchema": {
                "type": "object",
                "properties": {"server": {"type": "string"}},
                "required": ["server"],
            },
        },
        {
            "name": "mcp_call",
            "description": "Ponte p/ chamar uma tool de um servidor MCP EXTERNO (V18.6 E6). Allow-list dupla (servidor+tool) em config/mcp/clients.yaml.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server": {"type": "string"},
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["server", "tool"],
            },
        },
        {
            "name": "lilo_recall",
            "description": "Recall unificado da memoria (V18.4 E3): KV semantico (user/default/projeto) + notes.md + chats que batem com a query.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project_id": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "default": 5, "maximum": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "lilo_memory_semantic_search",
            "description": "Busca SEMANTICA na memoria (embeddings locais; V18.3 E2). Encontra por significado; sem Ollama degrada p/ busca textual.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "namespace": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "default": 5, "maximum": 50},
                },
                "required": ["query"],
            },
        },
        {
            "name": "lilo_memory_search",
            "description": "Busca textual (substring case-insensitive) em key, value e tags da memoria.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "namespace": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "default": 50, "maximum": 200},
                },
                "required": ["query"],
            },
        },
        {
            "name": "lilo_memory_stats",
            "description": "Estatisticas da memoria: total, por namespace, expirados, tamanho do DB.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "lilo_memory_export",
            "description": "Exporta entradas da memoria como JSON (backup). Filtre por namespace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "default": ""},
                },
            },
        },
        {
            "name": "lilo_memory_cleanup",
            "description": "Remove todas as entradas expiradas (housekeeping). Retorna a contagem.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ])

    # Cost tracker (consumo de modelos por dia/request)
    tools.extend([
        {
            "name": "lilo_cost_today",
            "description": "Resumo de uso e custo de modelos no dia (por backend e por subagente). JSON.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_date": {"type": "string", "description": "YYYY-MM-DD (default: hoje)", "default": ""},
                },
            },
        },
        {
            "name": "lilo_cost_recent",
            "description": "Ultimas N requests LLM com modelo, custo e duracao.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
                },
            },
        },
    ])

    # Ollama model manager (util ao mudar de maquina)
    tools.extend([
        {
            "name": "lilo_pull_model",
            "description": "Faz `ollama pull <name>` para baixar modelo do Hub. Util ao trocar de maquina.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome do modelo (ex: llama3.1:8b-instruct-q8_0)"},
                    "timeout": {"type": "integer", "description": "Timeout em segundos (default 600)", "default": 600},
                },
                "required": ["name"],
            },
        },
        {
            "name": "lilo_list_local_models",
            "description": "Lista modelos Ollama instalados localmente (`ollama list`).",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ])

    # Skills geradas automaticamente (lilo_skills/)
    try:
        from lilo_skills import load_skills_as_tools
        skill_tools = load_skills_as_tools()
        tools.extend(skill_tools)
        log.info(f"Skills carregadas: {len(skill_tools)}")
    except Exception as e:
        log.debug(f"Skills nao disponiveis: {e}")

    return tools


# V15 FASE 4: tools SENSIVEIS (escrita/exec) p/ o gate central de handle_tool_call.
# Tools de leitura/analise (scholar/prism_analyze/pdf/sql...) NAO entram. Default
# exec_mode 'auto' -> gate e no-op; em plan/ask passam a ser confirmadas/bloqueadas.
_TOOL_KIND = {
    "create_agent_scaffold": "python",   # escreve agents/<x>/agent.py + py_compile
    "make_report_docx": "write", "make_docx": "write",
    "make_xlsx": "write", "make_pptx": "write",
    "paper_build": "shell",              # roda bash assets/build.sh
}


def handle_tool_call(tool_name, arguments):
    """Executa uma tool MCP de forma centralizada. Retorna texto."""
    if tool_name == "lilo_health":
        return health_check()

    if tool_name == "lilo_models":
        agents = _load_agents()
        gw = agents.get("gateway")
        if gw and hasattr(gw, "list_models"):
            models = gw.list_models()
            return "Modelos:\n" + "\n".join(f"- {m}" for m in models)
        return "[LILO] Gateway nao disponivel."

    # Web search
    if tool_name == "web_search":
        try:
            from shared.web_search import search_and_summarize
            query = arguments.get("query", "")
            max_r = arguments.get("max_results", 5)
            return search_and_summarize(query, max_results=max_r)
        except Exception as e:
            return f"[LILO] Erro web_search: {e}"

    if tool_name == "web_fetch":
        try:
            from shared.web_search import fetch_page
            url = arguments.get("url", "")
            max_c = arguments.get("max_chars", 5000)
            return fetch_page(url, max_chars=max_c)
        except Exception as e:
            return f"[LILO] Erro web_fetch: {e}"

    # Skills geradas (prefixos skill_ e skill_advanced_)
    if tool_name.startswith("skill_"):
        try:
            from lilo_skills import call_skill
            return call_skill(tool_name, arguments)
        except Exception as e:
            return f"[LILO] Erro na skill {tool_name}: {e}"

    # ---- Memoria persistente (KV SQLite) ------------------------------------
    if tool_name == "lilo_memory_set":
        try:
            from shared.kv_memory import get_memory
            key = arguments.get("key", "")
            value = arguments.get("value", "")
            ns = arguments.get("namespace", "default")
            tags = arguments.get("tags", "")
            ttl = arguments.get("ttl_seconds", None)
            if not key:
                return "[LILO] lilo_memory_set: 'key' obrigatorio"
            if not isinstance(value, str):
                import json as _j
                value = _j.dumps(value, ensure_ascii=False, default=str)
            ttl_int = int(ttl) if ttl not in (None, "", 0, "0") else None
            get_memory().set(key, value, ns=ns, tags=tags, ttl_seconds=ttl_int)
            ttl_msg = f", ttl={ttl_int}s" if ttl_int else ""
            return f"OK -- {ns}/{key} salvo ({len(value)} chars{ttl_msg})"
        except Exception as e:
            return f"[LILO] Erro lilo_memory_set: {e}"

    if tool_name == "lilo_memory_get":
        try:
            from shared.kv_memory import get_memory
            import json as _j
            key = arguments.get("key", "")
            ns = arguments.get("namespace", "default")
            if not key:
                return "[LILO] lilo_memory_get: 'key' obrigatorio"
            val = get_memory().get(key, ns=ns, default=None)
            if val is None:
                return f"[vazio] {ns}/{key} nao definido."
            return val if isinstance(val, str) else _j.dumps(val, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_get: {e}"

    if tool_name == "lilo_memory_list":
        try:
            from shared.kv_memory import get_memory
            import json as _j
            ns = arguments.get("namespace", "") or None
            tag = arguments.get("tag", "") or None
            rows = get_memory().list(ns=ns, tag=tag)
            if not rows:
                return "Memoria vazia."
            lines = []
            for r in rows[:50]:
                v = r["value"]
                if not isinstance(v, str):
                    v = _j.dumps(v, ensure_ascii=False)
                if len(v) > 80:
                    v = v[:77] + "..."
                lines.append(
                    "- [%s/%s] %s  (tags: %s, upd: %s)" % (
                        r["ns"], r["key"], v, r["tags"] or "-",
                        r["updated_at"][:19])
                )
            if len(rows) > 50:
                lines.append("... (%d a mais)" % (len(rows) - 50))
            return "\n".join(lines)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_list: {e}"

    if tool_name == "lilo_memory_delete":
        try:
            from shared.kv_memory import get_memory
            key = arguments.get("key", "")
            ns = arguments.get("namespace", "default")
            if not key:
                return "[LILO] lilo_memory_delete: 'key' obrigatorio"
            ok = get_memory().delete(key, ns=ns)
            return "OK -- removido" if ok else f"[nao encontrado] {ns}/{key}"
        except Exception as e:
            return f"[LILO] Erro lilo_memory_delete: {e}"

    if tool_name in ("git_status", "git_diff", "git_commit"):
        try:
            from shared import git_tools
            if tool_name == "git_status":
                return git_tools.git_status()
            if tool_name == "git_diff":
                return git_tools.git_diff(staged=bool(arguments.get("staged")))
            msg = arguments.get("message", "")
            if not msg:
                return "[LILO] git_commit: 'message' obrigatorio"
            return git_tools.git_commit(
                msg, add_all=bool(arguments.get("add_all", True)))
        except Exception as e:
            return f"[LILO] Erro {tool_name}: {e}"

    if tool_name == "dev_workflow":
        try:
            from shared.dev_workflow import run_dev_workflow
            msg = arguments.get("message", "")
            if not msg:
                return "[LILO] dev_workflow: 'message' obrigatorio"
            return run_dev_workflow(
                msg, test_target=arguments.get("test_target", ""),
                project_id=arguments.get("project_id", ""))
        except Exception as e:
            return f"[LILO] Erro dev_workflow: {e}"

    if tool_name in ("mcp_list_servers", "mcp_list_tools", "mcp_call"):
        try:
            from shared import mcp_client
            if tool_name == "mcp_list_servers":
                import json as _j
                servers = mcp_client.list_servers()
                if not servers:
                    return ("[mcp] nenhum servidor externo declarado "
                            "(config/mcp/clients.yaml). Ver E6.")
                return _j.dumps(servers, ensure_ascii=False, indent=1)
            server = arguments.get("server", "")
            if not server:
                return "[LILO] %s: 'server' obrigatorio" % tool_name
            if tool_name == "mcp_list_tools":
                return mcp_client.list_tools(server)
            tool = arguments.get("tool", "")
            if not tool:
                return "[LILO] mcp_call: 'tool' obrigatorio"
            args = arguments.get("args", {}) or {}
            if isinstance(args, str):
                import json as _j
                try:
                    args = _j.loads(args)
                except Exception:
                    args = {}
            return mcp_client.call_tool(server, tool, args)
        except Exception as e:
            return f"[LILO] Erro {tool_name}: {e}"

    if tool_name == "lilo_recall":
        try:
            from shared.memory_facade import recall
            query = arguments.get("query", "")
            if not query:
                return "[LILO] lilo_recall: 'query' obrigatorio"
            pid = arguments.get("project_id", "") or None
            k = max(1, min(int(arguments.get("limit", 5)), 20))
            return recall(query, project_id=pid, k=k)
        except Exception as e:
            return f"[LILO] Erro lilo_recall: {e}"

    if tool_name == "lilo_memory_semantic_search":
        try:
            from shared.kv_memory import get_memory
            import json as _j
            query = arguments.get("query", "")
            if not query:
                return "[LILO] lilo_memory_semantic_search: 'query' obrigatorio"
            ns = arguments.get("namespace", "") or None
            limit = max(1, min(int(arguments.get("limit", 5)), 50))
            rows = get_memory().search_semantic(query, ns=ns, limit=limit)
            if not rows:
                return f"[semantica] sem matches para {query!r}"
            fallback = rows[0].get("match") == "like_fallback"
            cab = ("[semantica (fallback textual: embeddings indisponiveis)]"
                   if fallback else "[semantica]")
            lines = ["%s %d match(es) para %r:" % (cab, len(rows), query)]
            for r in rows:
                v = r["value"]
                if not isinstance(v, str):
                    v = _j.dumps(v, ensure_ascii=False, default=str)
                if len(v) > 80:
                    v = v[:77] + "..."
                score = ("score %.2f" % r["score"]) if "score" in r else "-"
                lines.append("- [%s/%s] (%s) %s" % (r["ns"], r["key"], score, v))
            return "\n".join(lines)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_semantic_search: {e}"

    if tool_name == "lilo_memory_search":
        try:
            from shared.kv_memory import get_memory
            import json as _j
            query = arguments.get("query", "")
            if not query:
                return "[LILO] lilo_memory_search: 'query' obrigatorio"
            ns = arguments.get("namespace", "") or None
            limit = max(1, min(int(arguments.get("limit", 50)), 200))
            rows = get_memory().search(query, ns=ns, limit=limit)
            if not rows:
                return f"[busca] sem matches para {query!r}"
            lines = [f"[busca] {len(rows)} match(es) para {query!r}:"]
            for r in rows:
                v = r["value"]
                if not isinstance(v, str):
                    v = _j.dumps(v, ensure_ascii=False)
                if len(v) > 80:
                    v = v[:77] + "..."
                lines.append(
                    "- [%s/%s] %s  (tags: %s)" % (
                        r["ns"], r["key"], v, r["tags"] or "-")
                )
            return "\n".join(lines)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_search: {e}"

    if tool_name == "lilo_memory_stats":
        try:
            from shared.kv_memory import get_memory
            import json as _j
            return _j.dumps(get_memory().stats(), ensure_ascii=False, indent=2)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_stats: {e}"

    if tool_name == "lilo_memory_export":
        try:
            from shared.kv_memory import get_memory
            ns = arguments.get("namespace", "") or None
            return get_memory().export_json(ns=ns)
        except Exception as e:
            return f"[LILO] Erro lilo_memory_export: {e}"

    if tool_name == "lilo_memory_cleanup":
        try:
            from shared.kv_memory import get_memory
            n = get_memory().cleanup_expired()
            return f"OK -- {n} entradas expiradas removidas"
        except Exception as e:
            return f"[LILO] Erro lilo_memory_cleanup: {e}"

    # ---- Cost tracker (consumo de modelos) ----------------------------------
    if tool_name == "lilo_cost_today":
        try:
            from shared.cost_tracker import get_tracker
            import json as _j
            target = arguments.get("target_date", "") or None
            return _j.dumps(
                get_tracker().daily_summary(target_date=target),
                ensure_ascii=False, indent=2,
            )
        except Exception as e:
            return f"[LILO] Erro lilo_cost_today: {e}"

    if tool_name == "lilo_cost_recent":
        try:
            from shared.cost_tracker import get_tracker
            limit = max(1, min(int(arguments.get("limit", 20)), 200))
            rows = get_tracker().recent_requests(limit=limit)
            if not rows:
                return "Nenhuma request registrada."
            lines = []
            for r in rows:
                lines.append(
                    "- %s %s %-24s sub=%-8s $%.4f %dms | %s" % (
                        (r.get("timestamp", "") or "")[:19],
                        r.get("backend", ""),
                        (r.get("model", "") or "")[:24],
                        r.get("subagent", "-"),
                        r.get("cost_usd", 0) or 0,
                        r.get("duration_ms", 0) or 0,
                        r.get("query_preview", "") or "",
                    )
                )
            return "\n".join(lines)
        except Exception as e:
            return f"[LILO] Erro lilo_cost_recent: {e}"

    # ---- Ollama model manager (lilo_pull_model) -----------------------------
    if tool_name == "lilo_pull_model":
        try:
            import subprocess
            name = arguments.get("name", "").strip()
            if not name:
                return "[LILO] lilo_pull_model: 'name' obrigatorio"
            timeout = int(arguments.get("timeout", 600))
            # Lista whitelist: aceita qualquer nome de modelo Ollama.
            # Bloqueia comandos shell mascarados como nome de modelo.
            import re as _re
            if not _re.match(r"^[A-Za-z0-9._:/+\-]+$", name):
                return f"[LILO] nome invalido: {name!r}"
            log.info("Ollama pull -> %s (timeout=%ds)", name, timeout)
            r = subprocess.run(
                ["ollama", "pull", name],
                capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace",
            )
            return (
                "[exit=%d]\n--- STDOUT ---\n%s\n--- STDERR ---\n%s" % (
                    r.returncode,
                    (r.stdout or "")[:8000],
                    (r.stderr or "")[:2000],
                )
            )
        except subprocess.TimeoutExpired:
            return f"[LILO] timeout em ollama pull (>{timeout}s)"
        except FileNotFoundError:
            return "[LILO] ollama CLI nao encontrado no PATH"
        except Exception as e:
            return f"[LILO] Erro lilo_pull_model: {e}"

    if tool_name == "lilo_list_local_models":
        try:
            import subprocess
            r = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            return r.stdout if r.returncode == 0 else f"[ERRO] {r.stderr}"
        except FileNotFoundError:
            return "[LILO] ollama CLI nao encontrado no PATH"
        except Exception as e:
            return f"[LILO] Erro lilo_list_local_models: {e}"

    tool_map = get_tool_map()
    if tool_name not in tool_map:
        return f"[LILO] Tool desconhecida: {tool_name}"

    tab, ctx_builder = tool_map[tool_name]
    query = arguments.get("query", arguments.get("filter", ""))
    ctx = ctx_builder(arguments) if ctx_builder else {}

    # V15 FASE 4: gate CENTRAL no orquestrador -- garante que plan/ask valem p/
    # TODAS as tools sensiveis (write/exec), nao so o agente desktop. Default
    # 'auto' -> gate retorna None (no-op, zero regressao).
    _kind = _TOOL_KIND.get(tool_name)
    if _kind:
        try:
            from shared import exec_mode as _xm
            _g = _xm.gate(_kind, "%s %s" % (tool_name, str(arguments)[:120]))
            if _g:
                return _g
        except Exception:
            pass

    # V7 (2026-05-12): villa_explain_routing -- bypass de route()/policy
    # para nao logar custo nem invocar LLM completo. Chamamos diretamente
    # explain_routing() do agente Villa.
    if tool_name == "villa_explain_routing":
        try:
            agents = _load_agents()
            villa = agents.get("villa")
            if not villa or not hasattr(villa, "explain_routing"):
                return "[LILO] Villa nao carregado ou nao suporta explain_routing"
            import json as _j
            info = villa.explain_routing(
                query=query,
                allow_delegate=bool(ctx.get("allow_delegate", True)),
            )
            return _j.dumps(info, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"[LILO] Erro villa_explain_routing: {e}"

    return route(query, tab=tab, context=ctx)


# -- CLI -----------------------------------------------------------------------

def _build_parser():
    p = argparse.ArgumentParser(
        description="LILO -- Orquestrador de subagentes de IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python lilo.py "liste as tabelas disponiveis"
  python lilo.py sql "gere uma query para contar registros por especie"
  python lilo.py pdf "resumir" --file paper.pdf --mode introduction
  python lilo.py scholar "inibidores TcTR Trypanosoma"
  python lilo.py health
""",
    )
    p.add_argument("tab_or_query", nargs="?", help="Subagente (sql/pdf/scholar/gateway) ou query direta")
    p.add_argument("query", nargs="*",        help="Query (quando tab eh especificada)")
    p.add_argument("--file",  "-f",  default="", help="Caminho para arquivo (PDF, SQLite, etc.)")
    p.add_argument("--mode",  "-m",  default="", help="Modo de operacao (simple/introduction/methods)")
    p.add_argument("--table", "-t",  default="", help="Nome da tabela SQL")
    return p


def main():
    parser = _build_parser()
    args   = parser.parse_args()

    TABS = {"sql", "pdf", "scholar", "gateway", "prism", "villa"}

    if args.tab_or_query == "health":
        print(health_check())
        return

    if args.tab_or_query in TABS:
        tab   = args.tab_or_query
        query = " ".join(args.query)
    else:
        tab   = None
        query = args.tab_or_query or ""
        if args.query:
            query += " " + " ".join(args.query)

    if not query:
        parser.print_help()
        sys.exit(1)

    ctx = {}
    if args.file:
        ctx["file_path"] = args.file
    if args.mode:
        ctx["mode"] = args.mode
    if args.table:
        ctx["table"] = args.table

    # V15 FASE 4: contrato do CLI. Interativo (tty) sem LILO_EXEC_MODE definido
    # -> 'ask' (confirma acoes sensiveis via stdin [y/N]). Nao-interativo
    # (script/pipe) -> mantem o default p/ nao travar esperando input.
    from shared import exec_mode as _xm
    _interactive = bool(getattr(sys.stdin, "isatty", lambda: False)()
                        and getattr(sys.stdout, "isatty", lambda: False)())
    if _interactive and not os.getenv("LILO_EXEC_MODE"):
        _xm.set_mode("ask")

    resp = route(query, tab=tab, context=ctx)
    while _xm.is_confirm(resp) and _interactive:
        print(resp[len(_xm.CONFIRM_PREFIX):])
        try:
            ans = input("Confirmar e executar? [y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans in ("y", "s", "sim", "yes"):
            _xm.grant_once()
            resp = route(query, tab=tab, context=ctx)
        else:
            resp = "[LILO] Acao cancelada pelo usuario."
            break
    if _xm.is_confirm(resp) and not _interactive:
        # sem canal de confirmacao -> erro acionavel (nao trava)
        resp = (resp[len(_xm.CONFIRM_PREFIX):]
                + "\n\n[LILO] Sem terminal interativo para confirmar. Para uso "
                "scriptado/nao-interativo, defina LILO_EXEC_MODE=auto.")
    print(resp)


if __name__ == "__main__":
    main()
# end of lilo.py
