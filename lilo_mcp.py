"""
lilo_mcp.py -- Servidor MCP do LILO unificado (arch-v10)
========================================================
Usa FastMCP. Suporta tres profiles:
  - desktop  (default) -> todas as tools (Claude Desktop)
  - pycharm            -> conjunto reduzido (PyCharm AI Assistant)
  - http               -> reservado para o futuro lilo_api.py

Pre-requisito (uma vez):
    pip install mcp

Uso CLI:
    python lilo_mcp.py                  # profile desktop (default)
    python lilo_mcp.py --profile pycharm

Configurar em %APPDATA%\\Claude\\claude_desktop_config.json:
  {
    "mcpServers": {
      "lilo": {
        "command": "python",
        "args": ["C:\\\\...\\\\lilo_mcp.py"],
        "env": { "PYTHONPATH": "C:\\\\...\\\\IA.agente" }
      }
    }
  }
"""

import sys
import os
import json
import argparse
from pathlib import Path

LILO_ROOT = Path(__file__).parent
sys.path.insert(0, str(LILO_ROOT))
os.environ.setdefault("PYTHONPATH", str(LILO_ROOT))

# -- Profile selection (deve vir antes do registro das tools) ----------------
_PROFILE = os.environ.get("LILO_MCP_PROFILE", "desktop").lower()
for i, arg in enumerate(sys.argv):
    if arg == "--profile" and i + 1 < len(sys.argv):
        _PROFILE = sys.argv[i + 1].lower()
    elif arg.startswith("--profile="):
        _PROFILE = arg.split("=", 1)[1].lower()

# Conjuntos de tools por profile
# Profiles disponiveis:
#   - desktop : todas as tools (Claude Desktop, OpenClaw, Claude Code padrao)
#   - pycharm : conjunto reduzido focado em refactoring/codigo
#   - bio     : focado em biologia molecular / data science (PrismAI + Scholar + PDF + Villa)
#   - http    : reservado para lilo_api.py
_PROFILE_TOOLS = {
    "desktop": None,  # None = registra tudo
    "pycharm": {
        "lilo_chat", "lilo_sql", "lilo_pdf", "lilo_scholar",
        "lilo_health", "prism_analyze", "prism_classify",
        "prism_audit", "villa_pipeline", "villa_quick_ask",
        "villa_explain_routing",
        # Desktop Commander tools (essenciais no PyCharm para refatorar codigo)
        "fs_read", "fs_write", "fs_list", "fs_stat", "fs_search",
        "run_shell", "run_python",
        # Memoria + cost (uteis em qualquer cliente)
        "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
        "lilo_memory_delete", "lilo_cost_today", "lilo_cost_recent",
        # v10.3 -- memoria avancada
        "lilo_memory_search", "lilo_memory_stats", "lilo_memory_export",
        "lilo_memory_cleanup",
        # Ollama model manager (util ao trocar de maquina)
        "lilo_pull_model", "lilo_list_local_models",
        # Composed tools (reduzem round-trips MCP)
        "fs_batch_read", "fs_codemod", "grep_and_read",
    },
    "bio": {
        # Workflows de pesquisa biomolecular: estatistica, literatura, leitura de papers
        "lilo_chat", "lilo_health", "lilo_models",
        "lilo_pdf", "lilo_scholar", "lilo_sql",
        "prism_analyze", "prism_classify", "prism_audit",
        "villa_pipeline", "villa_quick_ask", "villa_explain_routing",
        "lilo_web_search", "lilo_web_fetch",
        # filesystem (somente leitura/listagem/busca, sem run_shell para seguranca)
        "fs_read", "fs_list", "fs_stat", "fs_search",
        # memoria persistente para acumular notas de pesquisa
        "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
        "lilo_memory_search", "lilo_memory_stats", "lilo_memory_export",
        # ollama
        "lilo_pull_model", "lilo_list_local_models",
        "lilo_cost_today", "lilo_cost_recent",
        # Composed tools (sem run_shell para seguranca)
        "fs_batch_read", "grep_and_read",
    },
    # 2026-05-08: profile 'opus' -- conjunto curado de 15 tools que
    # AGREGAM CAPACIDADE ao Claude Opus (internet, filesystem, exec local,
    # memoria persistente, pipeline estatistico, busca academica). Tools
    # redundantes com Opus (lilo_chat, lilo_pdf, villa_*, prism_audit, etc.)
    # ficam de fora -- Opus as chama via slash command (/lilo_chat ...) no
    # dashboard quando explicitamente solicitado pelo usuario.
    "opus": {
        # Internet (Opus nao tem acesso nativo no Claude Desktop)
        "lilo_web_search", "lilo_web_fetch",
        # Filesystem do PC (read/write/list/stat/search)
        "fs_read", "fs_write", "fs_list", "fs_stat", "fs_search",
        # Execucao local (Opus nao executa codigo)
        "run_python", "run_shell",
        # Memoria persistente entre sessoes
        "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
        "lilo_memory_search",
        # Pesquisa biomedica estruturada (vs web_search bruto)
        "lilo_scholar",
        # Pipeline estatistico em arquivo .xlsx/.csv
        "prism_analyze", "prism_classify",
        # Ollama (info)
        "lilo_list_local_models", "lilo_pull_model",
        # Composed tools que reduzem round-trips no Opus
        "fs_batch_read", "grep_and_read", "fs_codemod",
    },
    "http": None,
    # 2026-05-12: profile 'claude_code' -- enxuto, voltado ao Claude Code CLI.
    # Claude Code ja tem Read/Write/Bash/Glob/Grep nativos; este profile
    # exporta SOMENTE ferramentas que agregam capacidade complementar.
    # Evita conflito entre run_shell (LILO) e Bash (CC) e reduz ruido no
    # contexto do Sonnet.
    "claude_code": {
        # Pipeline multi-agente + delegate (uso especifico via slash)
        "villa_pipeline", "villa_quick_ask", "villa_explain_routing",
        # Pipeline estatistico (NAO redundante com Claude Code)
        "prism_analyze", "prism_classify", "prism_audit",
        # Pesquisa biomedica estruturada (PubMed/arXiv/bioRxiv)
        "lilo_scholar",
        # PDF cientifico (parsing + sumarizacao especializada em papers)
        "lilo_pdf",
        # Memoria persistente entre sessoes (KV SQLite)
        "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
        "lilo_memory_search", "lilo_memory_stats", "lilo_memory_export",
        "lilo_memory_delete", "lilo_memory_cleanup",
        # Cost tracking (visivel para o usuario)
        "lilo_cost_today", "lilo_cost_recent",
        # Ollama model manager (info + pull)
        "lilo_pull_model", "lilo_list_local_models",
        # Health
        "lilo_health", "lilo_models",
    },
}
# 2026-05-23: profile 'cowork' -- automacao Cowork sem usuario presente.
# Espelha o conjunto 'bio' (local-only, SEM run_shell/run_python, sem custo),
# alinhado a policy 'cowork' de shared/server_profile.py. Seguro para tarefas
# agendadas (scheduled tasks) que rodam sem supervisao.
_PROFILE_TOOLS["cowork"] = set(_PROFILE_TOOLS["bio"])


# V10 (2026-05-30): merge opcional de config/profiles.yaml. O YAML pode
# (a) adicionar perfis novos, (b) substituir o conjunto de tools de um
# perfil existente, (c) resolver aliases (ex: 'pycharm' -> 'pycharm_assistant').
# Zero quebra se o YAML nao existir.
# Sentinel: "manter o conjunto de tools embarcado em _PROFILE_TOOLS".
_KEEP_DEFAULTS = "__KEEP_DEFAULTS__"


def _load_profiles_yaml_tools(profile_name):
    """Retorna (effective_profile, tools) lendo config/profiles.yaml.

    - effective_profile: nome resolvido via 'aliases' (ou o proprio nome).
    - tools:
        * set[str] -> filtro explicito
        * None     -> 'todas as tools' (campo mcp_tools=null no YAML)
        * _KEEP_DEFAULTS -> YAML ausente ou perfil sem mcp_tools; usar
          _PROFILE_TOOLS embarcado.
    """
    yaml_path = LILO_ROOT / "config" / "profiles.yaml"
    if not yaml_path.exists():
        return profile_name, _KEEP_DEFAULTS
    try:
        import yaml as _yaml
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = _yaml.safe_load(fh) or {}
    except Exception:
        return profile_name, _KEEP_DEFAULTS
    aliases = data.get("aliases") or {}
    if isinstance(aliases, dict):
        profile_name = aliases.get(profile_name, profile_name)
    yprofiles = (data.get("profiles") or {})
    conf = yprofiles.get(profile_name) if isinstance(yprofiles, dict) else None
    if not isinstance(conf, dict) or "mcp_tools" not in conf:
        return profile_name, _KEEP_DEFAULTS
    tools = conf.get("mcp_tools")
    if tools is None:
        return profile_name, None  # mcp_tools: null no YAML -> todas
    if isinstance(tools, list):
        return profile_name, set(str(t) for t in tools)
    return profile_name, _KEEP_DEFAULTS


_effective_profile, _yaml_tools = _load_profiles_yaml_tools(_PROFILE)
_PROFILE = _effective_profile  # resolver alias antes de _ALLOWED
if _yaml_tools == _KEEP_DEFAULTS:
    _ALLOWED = _PROFILE_TOOLS.get(_PROFILE)
else:
    _ALLOWED = _yaml_tools  # set ou None (None = todas)
    sys.stderr.write("[LILO] profile '%s' carregado via config/profiles.yaml (%s tools)\n" % (
        _PROFILE, "all" if _ALLOWED is None else str(len(_ALLOWED))))

# Instalar mcp se necessario (ANTES de qualquer @_profile_tool)
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    import subprocess
    sys.stderr.write("[LILO] Instalando pacote 'mcp'...\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "mcp>=1.0.0"])
    from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lilo")


# Tools idempotentes e caras -> elegiveis a cache TTL (P1, V14.6). Sao
# read-only e deterministicas o bastante para reaproveitar a saida na mesma
# sessao (o Claude reconsulta a mesma busca varias vezes). Excluidas: tudo que
# escreve (fs_write/run_*), consulta estado vivo (health/cost/models) ou e
# barato (memory get/list).
_CACHEABLE_TOOLS = {
    "lilo_scholar", "lilo_web_search", "lilo_web_fetch",
    "prism_classify", "lilo_skill_info", "lilo_list_skills",
}


def _budget_wrap(fn):
    """Envolve a tool com a guarda de orcamento de saida (V14.5).

    Corta saidas grandes num unico ponto -> reduz tokens injetados no contexto
    do Claude por TODAS as tools. functools.wraps preserva nome/doc/assinatura
    (inspect.signature segue __wrapped__), entao o schema MCP fica intacto.
    Falhas na guarda nunca derrubam a tool: devolve a saida crua.

    Para tools idempotentes (`_CACHEABLE_TOOLS`), aplica tambem o cache TTL
    (P1/V14.6): cache e a camada INTERNA (guarda o resultado cru), o orcamento
    e a EXTERNA (corta na saida). Assim um hit de cache tambem respeita o teto.
    """
    import functools
    from shared.mcp_budget import clamp_output

    cacheable = fn.__name__ in _CACHEABLE_TOOLS

    @functools.wraps(fn)
    def _wrapped(*args, **kwargs):
        if cacheable:
            try:
                from shared.mcp_cache import cached_call
                out = cached_call(fn.__name__, fn, args, kwargs)
            except Exception:
                out = fn(*args, **kwargs)
        else:
            out = fn(*args, **kwargs)
        try:
            clamped = clamp_output(out)
            # Telemetria V14.7: registra chars poupados quando cortou.
            if isinstance(out, str) and isinstance(clamped, str) \
                    and len(clamped) < len(out):
                try:
                    from shared.metrics import record_budget
                    record_budget(fn.__name__, len(out) - len(clamped))
                except Exception:
                    pass
            return clamped
        except Exception:
            return out

    return _wrapped


def _profile_tool(fn):
    """Decorator: registra a tool no FastMCP somente se ela passar no filtro do profile.
    DEFINIDO APOS `mcp = FastMCP(...)` para evitar NameError no decorator."""
    if _ALLOWED is None or fn.__name__ in _ALLOWED:
        return mcp.tool()(_budget_wrap(fn))
    return fn  # nao registra, mas mantem a funcao importavel para testes

# -- Lazy init ---------------------------------------------------------------
_lilo_loaded = False

def _ensure_lilo():
    """Carrega .env apenas uma vez (lazy). Erros sao silenciados para nao
    derrubar o servidor MCP -- se .env estiver ausente, agentes individuais
    falharao quando chamados (e a mensagem de erro vai pra resposta da tool)."""
    global _lilo_loaded
    if not _lilo_loaded:
        try:
            from shared.utils import load_env
            load_env()
        except Exception as e:
            # Logar em stderr mas nao crashar o servidor
            sys.stderr.write(f"[LILO MCP] aviso: load_env falhou: {e}\n")
            sys.stderr.flush()
        _lilo_loaded = True


# =============================================================================
# TOOLS CORE -- Sub-agentes LILO
# =============================================================================

@_profile_tool
def lilo_chat(query: str, mode: str = "chat", model: str = "") -> str:
    """Chat com LILO. Usa Ollama local ou Claude conforme complexidade.
    Modos: chat, code, bioinfo, sql.
    Args:
        query: Pergunta ou comando
        mode: Modo de operacao (chat/code/bioinfo/sql)
        model: Modelo especifico (opcional)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query, "mode": mode}
    if model:
        args["model"] = model
    return handle_tool_call("lilo_chat", args)


@_profile_tool
def lilo_sql(query: str, db_path: str = "", table: str = "") -> str:
    """Analise SQL: queries, estatisticas, ANOVA, t-test, regressao.
    Args:
        query: Pergunta sobre dados ou query SQL direta
        db_path: Caminho do banco SQLite (opcional)
        table: Nome da tabela (opcional)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query}
    if db_path:
        args["db_path"] = db_path
    if table:
        args["table"] = table
    return handle_tool_call("sql_query", args)


@_profile_tool
def lilo_pdf(query: str, file_path: str = "", mode: str = "simple") -> str:
    """Sumariza ou analisa PDFs cientificos.
    Args:
        query: O que fazer com o PDF
        file_path: Caminho do arquivo PDF
        mode: simple, introduction, methods, results
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query, "mode": mode}
    if file_path:
        args["file_path"] = file_path
    return handle_tool_call("pdf_summarize", args)


@_profile_tool
def lilo_scholar(query: str, source: str = "auto", max_results: int = 5, synthesize: bool = True) -> str:
    """Busca estruturada em fontes cientificas/biomedicas externas. Retorna
    lista de itens com {title, authors, year, source, url, ...}.
    Quando synthesize=True, agrega resultados em sintese critica curta.

    Fontes publicas (sem chave, paridade com o Claude): pubmed, arxiv,
    clinicaltrials (ClinicalTrials.gov), opentargets (alvos/gene-doenca),
    npi (provedores de saude EUA), crossref (DOIs/metadados),
    semanticscholar. source='all' agrega todas; 'auto'=pubmed+arxiv.

    USE WHEN: o usuario pede literatura academica especifica
    (revisao, papers recentes sobre X, drug targets, mecanismo
    molecular). Sempre prefira esta tool a lilo_web_search para
    pesquisa biomedica -- esta retorna metadados estruturados,
    web_search retorna so links.

    DO NOT USE WHEN: voce ja tem o DOI/URL especifico (use
    lilo_web_fetch). Tambem nao use para topicos nao-academicos.

    Exemplo: lilo_scholar("trypanothione reductase Trypanosoma cruzi
    inhibitors 2024", source="pubmed", max_results=8, synthesize=True)

    Args:
        query: Termos de busca (ingles funciona melhor).
        source: 'auto'|'all'|'pubmed'|'arxiv'|'clinicaltrials'|
                'opentargets'|'npi'|'crossref'|'semanticscholar'.
        max_results: 1-25 (default 5).
        synthesize: True (default) para sintese; False para so a lista.
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    tool = "scholar_synthesize" if synthesize else "scholar_search"
    return handle_tool_call(tool, {
        "query": query, "source": source, "max_results": max_results
    })


@_profile_tool
def lilo_health() -> str:
    """Verifica status de todos os subagentes LILO, Ollama, GPU e backends."""
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_health", {})


@_profile_tool
def lilo_models() -> str:
    """Lista modelos LLM disponiveis no Ollama."""
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_models", {})


# =============================================================================
# PRISM AI -- Analise cientifica automatizada
# =============================================================================

@_profile_tool
def prism_analyze(file_path: str, output_dir: str = "", language: str = "en", alpha: float = 0.05) -> str:
    """Pipeline cientifico completo sobre um .xlsx ou .csv: detecta
    desenho experimental, escolhe teste apropriado (t-test, ANOVA,
    Mann-Whitney, Kruskal-Wallis), checa premissas (normalidade
    Shapiro-Wilk, homocedasticidade Levene), gera boxplot publication-
    ready (PDF + PNG 300dpi), grava texto de Resultados em ingles ou
    portugues. Tudo reproduzivel.

    USE WHEN: usuario tem dados experimentais em arquivo (.xlsx, .csv,
    .tsv) e quer analise estatistica COMPLETA + grafico + texto. Voce
    nao tem como executar pandas/scipy/matplotlib direto -- esta tool
    faz tudo offline com o ambiente conda do usuario.

    DO NOT USE WHEN: usuario so quer entender qual teste escolher
    (responda direto). Tambem nao use se o arquivo nao existe ainda
    (peca para ele criar/colar primeiro).

    Exemplo: prism_analyze("D:/dados/exp_drug.xlsx",
    output_dir="D:/dados/resultados", language="pt", alpha=0.05)

    Args:
        file_path: Caminho absoluto para .xlsx/.csv/.tsv.
        output_dir: Pasta de saida (opcional; default = mesma pasta).
        language: 'en' (default) | 'pt'.
        alpha: 0.001-0.20 (default 0.05).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("prism_analyze", {
        "query": "analyze " + file_path,
        "file_path": file_path, "output_dir": output_dir,
        "language": language, "alpha": alpha,
    })


@_profile_tool
def prism_classify(file_path: str) -> str:
    """Inspeciona um arquivo de dados e CLASSIFICA o tipo de experimento
    (independent groups vs paired vs repeated measures vs correlation),
    sem rodar a analise. Retorna recomendacao de teste estatistico.

    USE WHEN: voce nao sabe se o experimento eh paired/independent ou
    qual teste escolher antes de chamar prism_analyze. Util como
    diagnostico rapido (mais barato que prism_analyze).

    DO NOT USE WHEN: voce ja sabe o desenho (chame prism_analyze direto).

    Exemplo: prism_classify("D:/dados/exp_drug.xlsx")

    Args:
        file_path: Caminho absoluto para .xlsx/.csv/.tsv.
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("prism_classify", {
        "query": "classify " + file_path, "file_path": file_path
    })


@_profile_tool
def prism_audit(file_path: str, claimed_test: str = "") -> str:
    """Audita analise estatistica: detecta erros, sugere correcoes.
    Args:
        file_path: Caminho para arquivo de dados
        claimed_test: Teste estatistico usado (para auditoria)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": "audit " + file_path, "file_path": file_path}
    if claimed_test:
        args["claimed_test"] = claimed_test
    return handle_tool_call("prism_audit", args)


# =============================================================================
# VILLA LOBOS -- Pipeline multi-agente
# =============================================================================

@_profile_tool
def villa_pipeline(task: str, iterations: int = 1, use_reader: bool = True, base_path: str = ".") -> str:
    """Pipeline completo Villa Lobos (5 agentes):
    Orchestrator > Planner > Reader > Worker > Reporter.
    Para tarefas complexas que requerem planejamento e execucao.
    Args:
        task: Tarefa a executar
        iterations: Iteracoes do Worker (1-5)
        use_reader: Analisar arquivos do projeto
        base_path: Caminho do projeto para o Reader
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("villa_pipeline", {
        "query": task, "iterations": iterations,
        "use_reader": use_reader, "base_path": base_path,
    })


@_profile_tool
def villa_quick_ask(question: str, agent: str = "worker") -> str:
    """Pergunta rapida a um agente Villa Lobos (sem pipeline completo).
    Args:
        question: Pergunta ou prompt
        agent: orchestrator, planner, reader, worker, reporter
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("villa_quick_ask", {
        "query": question, "agent": agent
    })


@_profile_tool
def villa_explain_routing(task: str, allow_delegate: bool = True) -> str:
    """[DEBUG] Descreve o roteamento que Villa Lobos faria SEM executar
    o pipeline. Retorna JSON com decision do Orchestrator, dominio
    heuristico, delegate target, stages planejados, tiers e stats de cache.

    USE WHEN: precisa entender por que o Villa pulou ou nao um estagio;
    quer validar mudancas em config/villa/domains.yaml; debug de roteamento.

    DO NOT USE WHEN: voce quer a resposta para a query (use villa_pipeline
    ou villa_quick_ask).

    Args:
        task: Tarefa que seria roteada.
        allow_delegate: Se True, considera delegacao a especialistas.
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("villa_explain_routing", {
        "query": task, "allow_delegate": allow_delegate
    })


# =============================================================================
# WEB SEARCH -- Busca na internet
# =============================================================================

@_profile_tool
def lilo_web_search(query: str, max_results: int = 5) -> str:
    """Busca web via DuckDuckGo, filtrada para dominios confiaveis (PubMed,
    arXiv, Nature, Science, Cell, bioRxiv, Wikipedia, GitHub, etc.).
    Retorna lista de {title, url, snippet}.

    USE WHEN: o usuario faz pergunta que requer informacao recente, dados
    cientificos atualizados, repositorios, ou referencias de literatura, e
    voce nao tem essa informacao no contexto. Sempre prefira esta tool a
    "chutar" URLs ou citar de memoria.

    DO NOT USE WHEN: o usuario apenas pediu explicacao conceitual de algo
    consolidado (ex: "como funciona PCR"). Resposta direta economiza tokens.

    Exemplo: lilo_web_search("CRISPR base editing 2025 review", max_results=5)

    Args:
        query: Termos de busca em ingles tendem a render melhor.
        max_results: 1-15 (default 5).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("web_search", {
        "query": query, "max_results": max_results
    })


@_profile_tool
def lilo_web_fetch(url: str, max_chars: int = 5000) -> str:
    """Baixa o conteudo textual de uma URL (apenas dominios da allow-list).
    HTML e convertido para texto limpo. Truncado em max_chars para nao
    explodir o contexto.

    USE WHEN: voce ja tem uma URL especifica (vinda de lilo_web_search,
    lilo_scholar, ou fornecida pelo usuario) e precisa do CONTEUDO real
    dela -- ex: ler um abstract do PubMed, baixar um README do GitHub.

    DO NOT USE WHEN: voce esta tentando navegar/explorar o site ou nao
    sabe a URL exata (use lilo_web_search primeiro).

    Exemplo: lilo_web_fetch("https://pubmed.ncbi.nlm.nih.gov/39123456/",
    max_chars=8000)

    Args:
        url: URL completa (https://...).
        max_chars: 500-50000 (default 5000).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("web_fetch", {
        "url": url, "max_chars": max_chars
    })


# =============================================================================
# DESKTOP COMMANDER -- filesystem + shell (allow-list em LILO_DESKTOP_ALLOW)
# =============================================================================

@_profile_tool
def fs_read(path: str, max_bytes: int = 200000) -> str:
    """Le arquivo texto (UTF-8) do PC. Respeita allow-list LILO_DESKTOP_ALLOW.

    Args:
        path: Caminho absoluto.
        max_bytes: 1024-2000000 (default 200000).
    """
    _ensure_lilo()
    from agents.desktop.agent import fs_read as _fr
    return _fr(path, max_bytes)


@_profile_tool
def fs_write(path: str, content: str, append: bool = False) -> str:
    """Escreve/anexa arquivo UTF-8. Cria dirs. Respeita allow-list.

    Args:
        path: Caminho absoluto.
        content: Conteudo UTF-8.
        append: True anexa; False (default) sobrescreve.
    """
    _ensure_lilo()
    from agents.desktop.agent import fs_write as _fw
    return _fw(path, content, append)


@_profile_tool
def fs_list(path: str, glob: str = "*", recursive: bool = False, limit: int = 200) -> str:
    """Lista diretorio com filtro glob. Retorna nome, tipo e tamanho.

    Args:
        path: Diretorio raiz.
        glob: ex. '*.py', '**/*.md'.
        recursive: True para descer subpastas.
        limit: 1-2000 (default 200).
    """
    _ensure_lilo()
    from agents.desktop.agent import fs_list as _fl
    return _fl(path, glob, recursive, limit)


@_profile_tool
def fs_stat(path: str) -> str:
    """Metadados (tipo, tamanho, mtime, perms).

    Args:
        path: Caminho absoluto.
    """
    _ensure_lilo()
    from agents.desktop.agent import fs_stat as _fs
    return _fs(path)


@_profile_tool
def fs_search(root: str, pattern: str, regex: bool = False, limit: int = 50) -> str:
    """Grep recursivo. Retorna path:linha:trecho.

    Args:
        root: Diretorio raiz.
        pattern: Substring ou regex.
        regex: False (default) ou True.
        limit: 1-500 (default 50).
    """
    _ensure_lilo()
    from agents.desktop.agent import fs_search as _fsr
    return _fsr(root, pattern, regex, limit)


@_profile_tool
def run_shell(cmd: str, cwd: str = "", timeout: int = 60) -> str:
    """Executa shell (PowerShell/bash). Comandos destrutivos bloqueados.
    Retorna stdout+stderr+exit. Respeita allow-list em cwd.

    Args:
        cmd: Comando.
        cwd: Diretorio de trabalho (opcional).
        timeout: 1-600 segundos (default 60).
    """
    _ensure_lilo()
    from agents.desktop.agent import run_shell as _rs
    return _rs(cmd, cwd or None, timeout)


@_profile_tool
def run_python(code: str, timeout: int = 60) -> str:
    """Executa Python em subprocess com numpy/pandas/scipy/biopython.
    Use print() para retornar valores.

    Args:
        code: Codigo Python.
        timeout: 1-300 segundos (default 60).
    """
    _ensure_lilo()
    from agents.desktop.agent import run_python as _rp
    return _rp(code, timeout)


# =============================================================================
# COMPOSED TOOLS (LILO Desktop Commander+) -- reduzem round-trips MCP
# =============================================================================

@_profile_tool
def fs_batch_read(paths: list, max_bytes_each: int = 100000) -> str:
    """Le N arquivos em 1 chamada. Retorna JSON {_summary, files}.
    Use para batches >=4 arquivos (economiza round-trips).

    Args:
        paths: Lista de caminhos absolutos.
        max_bytes_each: 1024-2000000 (default 100000).
    """
    _ensure_lilo()
    from agents.desktop.composed import fs_batch_read as _f
    return _f(paths, max_bytes_each)


@_profile_tool
def fs_codemod(path: str, find: str, replace: str,
               regex: bool = False, count: int = 0) -> str:
    """Find-and-replace em arquivo (UTF-8). Retorna count + amostras.

    Args:
        path: Caminho absoluto.
        find: Substring ou regex.
        replace: Texto (use \\1 \\2 para regex groups).
        regex: False (default) ou True.
        count: 0 (todas) ou N max.
    """
    _ensure_lilo()
    from agents.desktop.composed import fs_codemod as _f
    return _f(path, find, replace, regex, count)

@_profile_tool
def grep_and_read(root: str, pattern: str, regex: bool = False,
                  context_lines: int = 3, limit: int = 20) -> str:
    """Grep + retorna trechos com contexto antes/depois.

    Args:
        root: Diretorio raiz.
        pattern: Substring ou regex.
        regex: False (default) ou True.
        context_lines: 0-20 (default 3).
        limit: 1-100 blocos (default 20).
    """
    _ensure_lilo()
    from agents.desktop.composed import grep_and_read as _f
    return _f(root, pattern, regex, context_lines, limit)


# =============================================================================
# SKILLS -- Funcoes geradas do Conda (199 skills)
# =============================================================================

@_profile_tool
def lilo_list_skills(tag: str = "", package: str = "", search: str = "") -> str:
    """Lista skills disponiveis do LILO (199 funcoes de scipy, numpy,
    pandas, biopython, etc). Use para descobrir skills antes de executar.
    Args:
        tag: Filtrar por tag (estatistica, bioinformatica, visualizacao, etc)
        package: Filtrar por pacote (scipy, numpy, pandas, etc)
        search: Buscar por nome
    """
    _ensure_lilo()
    try:
        from lilo_skills import list_available_skills
        skills = list_available_skills(tags=[tag] if tag else None)
        if package:
            skills = [s for s in skills if s.get("package", "") == package]
        if search:
            skills = [s for s in skills if search.lower() in s["name"].lower()]
        if len(skills) > 30:
            return f"{len(skills)} skills (mostrando 30):\n" + "\n".join(
                f"- {s['name']}: {s.get('description','')[:60]}" for s in skills[:30])
        return "\n".join(f"- {s['name']}: {s.get('description','')[:80]}" for s in skills)
    except Exception as e:
        return f"[ERRO] {e}"


@_profile_tool
def lilo_run_skill(skill_name: str, arguments: str = "{}") -> str:
    """Executa uma skill LILO pelo nome.
    Args:
        skill_name: Nome da skill (ex: scipy_ttest_ind, numpy_mean)
        arguments: JSON com argumentos
    """
    _ensure_lilo()
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        return "Erro: argumentos devem ser JSON valido."
    from lilo import handle_tool_call
    name = skill_name if skill_name.startswith("skill_") else "skill_" + skill_name
    return handle_tool_call(name, args)


@_profile_tool
def lilo_skill_info(skill_name: str) -> str:
    """Mostra schema detalhado de uma skill (parametros, tipos, defaults).
    Args:
        skill_name: Nome da skill
    """
    _ensure_lilo()
    schema_path = LILO_ROOT / "lilo_skills" / "schemas" / (skill_name + ".json")
    if not schema_path.exists():
        clean = skill_name.replace("skill_", "")
        schema_path = LILO_ROOT / "lilo_skills" / "schemas" / (clean + ".json")
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        return json.dumps(schema, indent=2, ensure_ascii=False)
    return f"Skill '{skill_name}' nao encontrada."


# =============================================================================
# MEMORIA PERSISTENTE -- key/value entre sessoes
# =============================================================================

@_profile_tool
def lilo_memory_set(key: str, value: str, namespace: str = "default", tags: str = "") -> str:
    """Salva um par key->value na memoria persistente do LILO (SQLite local).
    Sobrevive entre sessoes do Claude Desktop -- voce pode escrever hoje
    e ler amanha.

    USE WHEN: voce descobre/define algo durante a conversa que vale
    persistir -- preferencia do usuario, decisao tomada, caminho de
    arquivo importante, snippet recorrente, key/value de configuracao.

    DO NOT USE WHEN: a info esta apenas no contexto da conversa atual
    (sem necessidade de longo prazo).

    Exemplo: lilo_memory_set("dataset_principal",
    "D:/dados/Tcruzi_RNAseq_2026.xlsx", namespace="project_TcTR",
    tags="rnaseq,trypanosoma")

    Args:
        key: Identificador unico dentro do namespace (snake_case).
        value: String ou JSON serializado.
        namespace: 'default' | 'user' | 'project_<nome>' (organizacao).
        tags: Tags separadas por virgula (filtrar depois com _list/_search).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_set", {
        "key": key, "value": value, "namespace": namespace, "tags": tags,
    })


@_profile_tool
def lilo_memory_get(key: str, namespace: str = "default") -> str:
    """Le um valor previamente gravado com lilo_memory_set.

    USE WHEN: voce sabe a chave exata e precisa do valor (sem busca).
    Tipico no inicio da conversa, para recuperar contexto persistente.

    DO NOT USE WHEN: nao sabe a chave (use lilo_memory_search) ou quer
    listar tudo (use lilo_memory_list).

    Exemplo: lilo_memory_get("dataset_principal", namespace="project_TcTR")

    Args:
        key: Chave exata (case-sensitive).
        namespace: Mesmo usado no _set.
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_get", {"key": key, "namespace": namespace})


@_profile_tool
def lilo_memory_list(namespace: str = "", tag: str = "") -> str:
    """Lista entradas da memoria persistente. Sem filtros = lista tudo.

    USE WHEN: voce quer ver o que esta armazenado para decidir o que
    recuperar. Tipico no inicio de sessao para "se familiarizar" com
    o contexto persistente.

    DO NOT USE WHEN: voce ja sabe a chave (use _get) ou quer matching
    semantico (use _search).

    Exemplo: lilo_memory_list(namespace="project_TcTR", tag="rnaseq")

    Args:
        namespace: Filtrar por namespace (vazio = todos).
        tag: Filtrar por tag (vazio = todas).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_list", {"namespace": namespace, "tag": tag})


@_profile_tool
def lilo_memory_delete(key: str, namespace: str = "default") -> str:
    """Remove uma entrada da memoria persistente.
    Args:
        key: Chave a remover
        namespace: Categoria
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_delete", {"key": key, "namespace": namespace})


@_profile_tool
def lilo_memory_search(query: str, namespace: str = "", limit: int = 50) -> str:
    """Busca textual (substring, case-insensitive) em key + value + tags
    da memoria persistente. Retorna entradas que matcham.

    USE WHEN: voce nao sabe a chave exata mas tem uma palavra-chave
    do conteudo. Ex: "qual era o caminho do dataset de Tcruzi?".

    DO NOT USE WHEN: chave conhecida (use _get).

    Exemplo: lilo_memory_search("Tcruzi", namespace="", limit=10)

    Args:
        query: Termo de busca (substring).
        namespace: Filtrar (vazio = todos).
        limit: 1-200 (default 50).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_search", {
        "query": query, "namespace": namespace, "limit": limit,
    })


@_profile_tool
def lilo_memory_stats() -> str:
    """Estatisticas da memoria: total, por namespace, expirados,
    tamanho do DB. Util para diagnostico."""
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_stats", {})


@_profile_tool
def lilo_memory_export(namespace: str = "") -> str:
    """Exporta entradas da memoria como JSON (backup).
    Args:
        namespace: filtrar por ns (vazio = exporta tudo)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_export", {"namespace": namespace})


@_profile_tool
def lilo_memory_cleanup() -> str:
    """Remove todas as entradas expiradas (housekeeping)."""
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_memory_cleanup", {})


# =============================================================================
# COST TRACKING -- consumo de modelos
# =============================================================================

@_profile_tool
def lilo_cost_today(target_date: str = "") -> str:
    """Resumo de custo e uso de modelos no dia atual (ou data ISO especifica).
    Args:
        target_date: Data alvo no formato YYYY-MM-DD (default: hoje)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_cost_today", {"target_date": target_date})


@_profile_tool
def lilo_cost_recent(limit: int = 20) -> str:
    """Ultimas N requests LLM registradas (com modelo, custo, duracao).
    Args:
        limit: Numero de registros (default 20, max 200)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_cost_recent", {"limit": limit})


# =============================================================================
# OLLAMA MODEL MANAGER -- pull/list de modelos do Hub
# =============================================================================

@_profile_tool
def lilo_pull_model(name: str, timeout: int = 600) -> str:
    """Executa `ollama pull <name>` no PC do usuario para baixar
    um modelo do Hub Ollama. Util ao configurar nova maquina ou
    adicionar modelo configurado em VILLA_MODELS / .env.

    USE WHEN: usuario quer baixar um modelo Ollama especifico ou
    voce detecta (via lilo_list_local_models) que falta um modelo
    requerido para o pipeline.

    DO NOT USE WHEN: voce nao tem certeza do nome exato do modelo
    (peca para o usuario confirmar -- download pode ser pesado).

    Exemplo: lilo_pull_model("qwen2.5-coder:14b", timeout=900)

    Args:
        name: Nome no formato 'modelo:tag' (ex: 'llama3.1:8b-instruct-q8_0').
        timeout: 60-3600 segundos (default 600).
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_pull_model", {"name": name, "timeout": timeout})


@_profile_tool
def lilo_list_local_models() -> str:
    """Lista modelos Ollama instalados localmente no PC do usuario
    (output cru do `ollama list`: nome, tag, tamanho, data).

    USE WHEN: voce precisa saber se um modelo especifico esta
    disponivel antes de chamar villa_pipeline ou lilo_chat. Tambem
    util para sugerir qual modelo usar com base no que ja existe.

    DO NOT USE WHEN: a tarefa nao envolve modelo local Ollama
    (Opus ja e suficiente para a resposta).

    Exemplo: lilo_list_local_models()
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_list_local_models", {})


# =============================================================================
# ENTRYPOINT -- com logging robusto em stderr para Claude Desktop
# =============================================================================
# 2026-05-08: Adicionado wrapper try/except global e logging de stack trace
# em stderr para que crashes apareçam no log do Claude Desktop
# (%LOCALAPPDATA%\Claude\logs\mcp-server-lilo.log).

def _stderr_log(msg: str) -> None:
    """Logging unificado: sempre vai para stderr com flush imediato.

    Stderr e capturado pelo Claude Desktop em mcp-server-lilo.log; usar
    print() (stdout) pode interferir no protocolo MCP/JSON-RPC.
    """
    try:
        sys.stderr.write(msg.rstrip() + chr(10))
        sys.stderr.flush()
    except Exception:
        pass




# =============================================================================
# V10 (2026-05-30) -- villa_route: roteamento puro (sem executar pipeline)
# =============================================================================

@_profile_tool
def villa_route(task: str, allow_delegate: bool = True) -> str:
    """Retorna APENAS a decisao de roteamento do Villa_Lobos.

    Util quando o cliente quer saber se a tarefa seria delegada a um
    especialista (PRISM/SQL/PDF/Scholar) ou rodaria o pipeline completo,
    SEM gastar chamadas LLM dos stages de Worker/Reporter.

    Args:
        task: Tarefa em linguagem natural.
        allow_delegate: Se True, considera delegacao a especialista.
    """
    _ensure_lilo()
    try:
        from agents.villa_lobos.agent import VillaLobosAgent
        v = VillaLobosAgent()
        info = v.explain_routing(task, allow_delegate=allow_delegate)
        import json as _json
        return _json.dumps(info, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        return "[LILO] Erro villa_route: %s" % e


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    try:
        _stderr_log("[LILO MCP] starting (profile=%s, allowed=%s)" % (
            _PROFILE,
            ("<all>" if _ALLOWED is None else len(_ALLOWED)),
        ))
        mcp.run()
    except Exception as e:
        import traceback
        tb = traceback.format_exc().replace("\n", " | ")
        _stderr_log("[LILO MCP] CRASH: %s -- %s" % (e, tb))
        raise
