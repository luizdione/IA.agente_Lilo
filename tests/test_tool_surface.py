"""
tests/test_tool_surface.py -- REDE DE SEGURANÇA (F0) da consolidação de agentes.

Congela a superfície pública de tools/agentes/perfis. A consolidação 10→6
(Studio/Litera/DataLab/System via shims) NÃO pode fazer nenhuma tool ou agente
sumir -- estes testes falham se isso acontecer. Usa superset (⊇): adicionar é
livre; remover quebra. Se você REMOVER algo de propósito, atualize o golden aqui
no mesmo commit (é a assinatura da mudança).

Capturado em 2026-07-21 (antes da consolidação).
"""
from __future__ import annotations

import inspect
import re

# --- Golden: chaves do get_tool_map() (tool de domínio -> subagente) ----------
GOLDEN_TOOL_MAP = {
    "create_agent_scaffold", "lilo_chat", "lilo_health", "lilo_models",
    "make_docx", "make_pptx", "make_report_docx", "make_xlsx",
    "paper_build", "paper_draft", "paper_outline", "paper_references",
    "paper_section", "pdf_list", "pdf_search", "pdf_summarize",
    "prism_analyze", "prism_audit", "prism_classify", "prism_eda",
    "propose_agent", "scholar_review", "scholar_search", "scholar_synthesize",
    "sql_query", "sql_stats", "villa_explain_routing", "villa_pipeline",
    "villa_quick_ask",
}

# --- Golden: nomes de tools presentes em algum perfil MCP ----------------------
GOLDEN_PROFILE_TOOLS = {
    "create_agent_scaffold", "exec_env_info", "fs_batch_read", "fs_codemod",
    "fs_list", "fs_read", "fs_search", "fs_stat", "fs_write", "grep_and_read",
    "lilo_chat", "lilo_cost_recent", "lilo_cost_today", "lilo_health",
    "lilo_list_local_models", "lilo_memory_cleanup", "lilo_memory_delete",
    "lilo_memory_export", "lilo_memory_get", "lilo_memory_list",
    "lilo_memory_search", "lilo_memory_set", "lilo_memory_stats", "lilo_models",
    "lilo_pdf", "lilo_pull_model", "lilo_scholar", "lilo_sql", "lilo_web_fetch",
    "lilo_web_search", "list_conda_envs", "make_pptx", "make_report_docx",
    "make_xlsx", "paper_draft", "paper_references", "paper_section",
    "prism_analyze", "prism_audit", "prism_classify", "prism_eda", "run_python",
    "run_r", "run_shell", "run_wsl", "scholar_brain", "scholar_review",
    "villa_explain_routing", "villa_pipeline", "villa_quick_ask",
    # V20: sumarizacao local generica + parser de logs bioinfo (economia de tokens)
    "lilo_summarize_file", "parse_bio_log",
}

# --- Golden: nomes de subagentes registrados ----------------------------------
GOLDEN_AGENTS = {
    "sql", "pdf", "scholar", "prism", "villa", "gateway", "desktop",
    "paper", "docgen", "skillsmith",
}


def test_tool_map_keys_preserved():
    from lilo import get_tool_map
    have = set(get_tool_map().keys())
    missing = GOLDEN_TOOL_MAP - have
    assert not missing, "tools de domínio sumiram do get_tool_map: %s" % sorted(missing)


def test_profile_tools_preserved():
    from lilo_mcp import _PROFILE_TOOLS
    union: set = set()
    for s in _PROFILE_TOOLS.values():
        if isinstance(s, (set, list)):
            union |= set(s)
    missing = GOLDEN_PROFILE_TOOLS - union
    assert not missing, "tools sumiram dos perfis MCP: %s" % sorted(missing)


def test_agent_registry_preserved():
    # _AGENT_REGISTRY é local a _load_agents(); parseamos os nomes registrados.
    from lilo import _load_agents
    src = inspect.getsource(_load_agents)
    names = set(re.findall(r'\(\s*"(\w+)"\s*,\s*"agents', src))
    missing = GOLDEN_AGENTS - names
    assert not missing, ("subagentes sumiram do registry (a consolidação deve "
                         "registrar a instância fundida sob os nomes antigos): %s"
                         % sorted(missing))


def test_yaml_cobre_perfis_embarcados():
    """V20.1: config/profiles.yaml SOBRESCREVE _PROFILE_TOOLS quando o perfil tem
    mcp_tools como lista. Logo, toda tool declarada no canal EMBARCADO de um
    perfil deve tambem constar no YAML desse perfil -- senao ela fica MORTA (o
    YAML e que vigora). Este teste mede o canal EFETIVO e teria pego scholar_brain
    ausente do YAML de bio/cowork/claude_desktop/claude_code."""
    from lilo_mcp import (_PROFILE_TOOLS, _load_profiles_yaml_tools,
                          _KEEP_DEFAULTS)
    mortas = {}
    for name, emb in _PROFILE_TOOLS.items():
        if not isinstance(emb, set):
            continue  # None = todas as tools
        _eff, tools = _load_profiles_yaml_tools(name)
        if tools is None or tools == _KEEP_DEFAULTS:
            continue  # YAML nao restringe este perfil -> o embarcado ja vigora
        faltando = emb - set(tools)
        if faltando:
            mortas[name] = sorted(faltando)
    assert not mortas, ("tools no _PROFILE_TOOLS embarcado mas AUSENTES do YAML "
                        "(vigora o YAML -> ficam mortas): %s" % mortas)
