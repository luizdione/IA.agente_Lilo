"""
lilo_skills — Skills geradas automaticamente para o LILO
========================================================
Carrega skills do registry.json e expõe como tools MCP.

Uso:
    from lilo_skills import load_skills_as_tools, call_skill

    tools = load_skills_as_tools()           # lista de tool defs MCP
    result = call_skill("seaborn_axes_style", {"style": "darkgrid"})
"""

import json
import importlib.util
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path(__file__).parent / "skills"
SCHEMAS_DIR = Path(__file__).parent / "schemas"
REGISTRY_PATH = Path(__file__).parent / "registry.json"

# Versao do schema do registry.json. Incrementar quando mudar o formato
# (campos novos em skill, mudanca de tipo, renomeacao). O loader detecta
# divergencia e regera implicitamente avisando no log.
# Historico:
#   1.0  -- formato inicial (sem campo 'version')
#   1.1  -- adicionado campo 'version' + 'schema_version' no topo;
#           skills com complexity='high' ganham prefixo 'skill_advanced_'
SCHEMA_VERSION = "1.1"
MIN_REGISTRY_VERSION = "1.0"

# Skills com complexity high recebem este prefixo no nome MCP, separando-as
# das simples no menu / autocompletar. Nao afeta o nome da funcao Python no
# arquivo gerado em lilo_skills/skills/.
ADVANCED_PREFIX = "skill_advanced_"
NORMAL_PREFIX = "skill_"

_registry_cache: Optional[dict] = None

# 24 skills CORE expostas no chat e MCP (mapa nome -> tool real do handle_tool_call)
# Quando o usuario digita /lilo_chat ... no chat, o dashboard chama
# call_skill("lilo_chat", {...}); este mapa redireciona para o handler real.
CORE_SKILLS = {
    "lilo_chat":       ("lilo_chat",          None),
    "lilo_sql":        ("sql_query",          None),
    "lilo_pdf":        ("pdf_summarize",      None),
    "lilo_scholar":    ("scholar_synthesize", None),
    "lilo_health":     ("lilo_health",        None),
    "lilo_models":     ("lilo_models",        None),
    # v10.2 -- memoria persistente (KV SQLite)
    "lilo_memory_set":      ("lilo_memory_set",      None),
    "lilo_memory_get":      ("lilo_memory_get",      None),
    "lilo_memory_list":     ("lilo_memory_list",     None),
    "lilo_memory_delete":   ("lilo_memory_delete",   None),
    # v10.3 -- memoria avancada (search/stats/export/cleanup + TTL)
    "lilo_memory_search":   ("lilo_memory_search",   None),
    "lilo_memory_stats":    ("lilo_memory_stats",    None),
    "lilo_memory_export":   ("lilo_memory_export",   None),
    "lilo_memory_cleanup":  ("lilo_memory_cleanup",  None),
    # v10.2 -- cost tracker
    "lilo_cost_today":      ("lilo_cost_today",      None),
    "lilo_cost_recent":     ("lilo_cost_recent",     None),
    # v10.2 -- ollama model manager
    "lilo_pull_model":        ("lilo_pull_model",        None),
    "lilo_list_local_models": ("lilo_list_local_models", None),
    "prism_analyze":   ("prism_analyze",      None),
    "prism_classify":  ("prism_classify",     None),
    "prism_audit":     ("prism_audit",        None),
    "villa_pipeline":  ("villa_pipeline",     None),
    "villa_quick_ask": ("villa_quick_ask",    None),
    "lilo_web_search": ("web_search",         None),
    "lilo_web_fetch":  ("web_fetch",          None),
    # As 3 ultimas sao meta-skills resolvidas localmente (sem handle_tool_call)
    "lilo_list_skills": ("__local_list__",    None),
    "lilo_run_skill":   ("__local_run__",     None),
    "lilo_skill_info":  ("__local_info__",    None),
}


def _call_core_skill(skill_name: str, arguments: dict) -> str:
    """Roteia uma das 16 skills core para o handler correto em lilo.py
    ou para resolucao local (meta-skills)."""
    target, _ = CORE_SKILLS[skill_name]

    # Meta-skills: list/run/info — resolvem dentro deste modulo, sem lilo.py
    if target == "__local_list__":
        skills = list_available_skills(
            tags=[arguments["tag"]] if arguments.get("tag") else None
        )
        if arguments.get("package"):
            skills = [s for s in skills if s.get("package") == arguments["package"]]
        if arguments.get("search"):
            q = arguments["search"].lower()
            skills = [s for s in skills if q in s["name"].lower()]
        total = len(skills)
        if total > 30:
            skills = skills[:30]
            head = f"Mostrando 30 de {total} skills (use tag/package/search para filtrar):\n"
        else:
            head = f"{total} skills encontradas:\n"
        lines = [head] + [
            f"- {s['name']} ({s.get('package','')}) [{', '.join(s.get('tags', []))}]"
            for s in skills
        ]
        return "\n".join(lines)

    if target == "__local_run__":
        inner = arguments.get("skill_name", "")
        raw = arguments.get("arguments", "{}")
        try:
            inner_args = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return "Erro: arguments deve ser JSON valido."
        return call_skill(inner, inner_args)

    if target == "__local_info__":
        inner = arguments.get("skill_name", "")
        clean = inner.replace("skill_", "")
        sp = SCHEMAS_DIR / f"{clean}.json"
        if not sp.exists():
            return f"Skill '{inner}' nao encontrada. Use lilo_list_skills."
        with open(sp, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=2, ensure_ascii=False)

    # Tools normais — delegar para lilo.handle_tool_call
    # Caso especial: lilo_scholar com synthesize=False usa scholar_search
    if skill_name == "lilo_scholar" and str(arguments.get("synthesize", "true")).lower() == "false":
        target = "scholar_search"

    try:
        from lilo import handle_tool_call
        return handle_tool_call(target, arguments)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}", "skill": skill_name})


def _version_lt(a: str, b: str) -> bool:
    """True se versao 'a' for menor que 'b' (semver simples major.minor)."""
    try:
        ta = tuple(int(x) for x in a.split("."))
        tb = tuple(int(x) for x in b.split("."))
        return ta < tb
    except Exception:
        return False


def _load_registry() -> dict:
    """Carrega registry.json (com cache + check de schema_version).

    Se o registry tiver schema_version < MIN_REGISTRY_VERSION, emite warning
    no log mas continua carregando. Recomenda rodar `scan_conda_env.py +
    generate_skills.py` para regerar.
    """
    global _registry_cache
    if _registry_cache is None:
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                _registry_cache = json.load(f)
            ver = str(_registry_cache.get("schema_version", "1.0"))
            if _version_lt(ver, MIN_REGISTRY_VERSION):
                import sys as _sys
                _sys.stderr.write(
                    "[lilo_skills] registry.json schema_version=%s < %s. "
                    "Regenere com: python lilo_skills/scan_conda_env.py "
                    "&& python lilo_skills/generate_skills.py\n" % (
                        ver, MIN_REGISTRY_VERSION)
                )
        else:
            _registry_cache = {
                "skills": [], "total_skills": 0,
                "schema_version": SCHEMA_VERSION,
            }
    return _registry_cache


def _skill_mcp_name(skill: dict) -> str:
    """Calcula o nome MCP de uma skill (prefixo varia por complexity).

    - complexity='high'  -> skill_advanced_<name>
    - resto              -> skill_<name>

    O prefixo so aparece se ainda nao estiver presente, para tolerar
    chamadas com nome ja prefixado.
    """
    raw = skill.get("name", "")
    if raw.startswith(ADVANCED_PREFIX) or raw.startswith(NORMAL_PREFIX):
        return raw
    if str(skill.get("complexity", "")).lower() == "high":
        return ADVANCED_PREFIX + raw
    return NORMAL_PREFIX + raw


def load_skills_as_tools(
    tags: list[str] = None,
    packages: list[str] = None,
    include_advanced: bool = True,
) -> list[dict]:
    """
    Carrega skills como definições de tools MCP.

    Args:
        tags: filtrar por tags (ex: ["estatistica", "bioinformatica"])
        packages: filtrar por pacote fonte (ex: ["scipy", "numpy"])
        include_advanced: se False, omite skills com complexity='high'
                          (uteis para reduzir poluicao no menu / autocompletar
                          do dashboard)

    Returns:
        Lista de dicts compatíveis com MCP tools/list.
    """
    registry = _load_registry()
    tools = []

    for skill in registry.get("skills", []):
        # Filtros
        if tags and not any(t in skill.get("tags", []) for t in tags):
            continue
        if packages and skill.get("source_package", "") not in packages:
            continue
        if (not include_advanced) and str(
                skill.get("complexity", "")).lower() == "high":
            continue

        # Carregar schema
        schema_path = SCHEMAS_DIR / f"{skill['name']}.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            tools.append({
                "name": _skill_mcp_name(skill),
                "description": schema.get("description", ""),
                "inputSchema": schema.get("parameters", {
                    "type": "object", "properties": {}}),
            })

    return tools


def call_skill(skill_name: str, arguments: dict) -> str:
    """
    Executa uma skill pelo nome.

    Args:
        skill_name: nome da skill (com ou sem prefixo 'skill_')
        arguments: dict de argumentos

    Returns:
        Resultado em texto (JSON serializado ou string).
    """
    # Remover prefixo se presente (ordem importa: advanced antes do normal)
    if skill_name.startswith(ADVANCED_PREFIX):
        name = skill_name[len(ADVANCED_PREFIX):]
    elif skill_name.startswith(NORMAL_PREFIX):
        name = skill_name[len(NORMAL_PREFIX):]
    else:
        name = skill_name

    # 1) PRIMEIRO: tenta as 16 skills CORE (lilo_chat, prism_*, villa_*, etc).
    #    Isso resolve o erro "Skill 'lilo_chat' nao encontrada" que aparecia
    #    no chat — agora /lilo_chat, /lilo_sql, /prism_analyze etc funcionam.
    if name in CORE_SKILLS:
        return _call_core_skill(name, arguments or {})

    # 2) Fallback: skills geradas (arquivos .py em lilo_skills/skills/)
    skill_path = SKILLS_DIR / f"{name}.py"
    if not skill_path.exists():
        return json.dumps({"error": f"Skill '{name}' não encontrada"})

    try:
        spec = importlib.util.spec_from_file_location(name, str(skill_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        func = getattr(mod, name, None)
        if func is None:
            return json.dumps({"error": f"Função '{name}' não encontrada no módulo"})

        result = func(**arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}", "skill": name})


# Metadados das 16 skills CORE para aparecerem no menu /  do chat
_CORE_SKILL_META = [
    {"name": "lilo_chat",       "source_package": "lilo",  "tags": ["core", "chat"],          "complexity": "low",
     "description": "Chat com LILO (Ollama local ou Claude conforme complexidade)."},
    {"name": "lilo_sql",        "source_package": "lilo",  "tags": ["core", "sql", "stats"],  "complexity": "med",
     "description": "Analise SQL: queries, estatisticas, ANOVA, t-test, regressao."},
    {"name": "lilo_pdf",        "source_package": "lilo",  "tags": ["core", "pdf"],           "complexity": "med",
     "description": "Sumariza ou analisa PDFs cientificos."},
    {"name": "lilo_scholar",    "source_package": "lilo",  "tags": ["core", "scholar"],       "complexity": "med",
     "description": "Busca academica PubMed + arXiv com sintese de literatura."},
    {"name": "prism_analyze",   "source_package": "prism", "tags": ["core", "stats", "auto"], "complexity": "high",
     "description": "Analise cientifica completa: detecta experimento, testa hipoteses."},
    {"name": "prism_classify",  "source_package": "prism", "tags": ["core", "stats"],         "complexity": "med",
     "description": "Classifica tipo de experimento a partir dos dados."},
    {"name": "prism_audit",     "source_package": "prism", "tags": ["core", "stats"],         "complexity": "med",
     "description": "Audita analise estatistica: detecta erros, sugere correcoes."},
    {"name": "villa_pipeline",  "source_package": "villa", "tags": ["core", "pipeline"],      "complexity": "high",
     "description": "Pipeline completo Villa Lobos (5 agentes)."},
    {"name": "villa_quick_ask", "source_package": "villa", "tags": ["core", "agent"],         "complexity": "low",
     "description": "Pergunta rapida a um agente Villa Lobos."},
    {"name": "lilo_web_search", "source_package": "web",   "tags": ["core", "web"],           "complexity": "low",
     "description": "Busca na internet via DuckDuckGo (sites confiaveis)."},
    {"name": "lilo_web_fetch",  "source_package": "web",   "tags": ["core", "web"],           "complexity": "low",
     "description": "Busca conteudo de uma URL (apenas dominios confiaveis)."},
    {"name": "lilo_list_skills","source_package": "lilo",  "tags": ["core", "meta"],          "complexity": "low",
     "description": "Lista skills disponiveis do LILO."},
    {"name": "lilo_run_skill",  "source_package": "lilo",  "tags": ["core", "meta"],          "complexity": "low",
     "description": "Executa uma skill LILO pelo nome."},
    {"name": "lilo_skill_info", "source_package": "lilo",  "tags": ["core", "meta"],          "complexity": "low",
     "description": "Mostra schema detalhado de uma skill."},
    {"name": "lilo_health",     "source_package": "lilo",  "tags": ["core", "diag"],          "complexity": "low",
     "description": "Verifica status de subagentes LILO, Ollama, GPU e backends."},
    {"name": "lilo_models",     "source_package": "lilo",  "tags": ["core", "diag"],          "complexity": "low",
     "description": "Lista modelos LLM disponiveis no Ollama."},
    # v10.2 -- memoria persistente (KV SQLite, sobrevive entre sessoes)
    {"name": "lilo_memory_set",    "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Salva valor na memoria persistente do LILO. Args: key, value, namespace=default, tags=''."},
    {"name": "lilo_memory_get",    "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Le valor da memoria persistente. Args: key, namespace=default."},
    {"name": "lilo_memory_list",   "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Lista entradas da memoria persistente (filtros opcionais por namespace e tag)."},
    {"name": "lilo_memory_delete", "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Remove entrada da memoria persistente. Args: key, namespace=default."},
    # v10.3 -- memoria avancada
    {"name": "lilo_memory_search", "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Busca textual (substring) em key/value/tags da memoria. Args: query, namespace='', limit=50."},
    {"name": "lilo_memory_stats", "source_package": "lilo", "tags": ["core", "memory", "diag"], "complexity": "low",
     "description": "Estatisticas da memoria: total, por namespace, expirados, tamanho do DB."},
    {"name": "lilo_memory_export", "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Exporta entradas como JSON (backup). Filtra por namespace opcional."},
    {"name": "lilo_memory_cleanup", "source_package": "lilo", "tags": ["core", "memory"], "complexity": "low",
     "description": "Remove entradas expiradas (housekeeping)."},
    # v10.2 -- cost tracker
    {"name": "lilo_cost_today",    "source_package": "lilo", "tags": ["core", "cost"],   "complexity": "low",
     "description": "Resumo de uso e custo de modelos no dia (JSON: por backend e subagente)."},
    {"name": "lilo_cost_recent",   "source_package": "lilo", "tags": ["core", "cost"],   "complexity": "low",
     "description": "Ultimas N requests LLM (modelo, custo, duracao). Args: limit=20."},
    # v10.2 -- ollama model manager
    {"name": "lilo_pull_model",    "source_package": "lilo", "tags": ["core", "ollama"], "complexity": "low",
     "description": "Faz `ollama pull <name>` para baixar modelo. Util ao trocar de maquina. Args: name, timeout=600."},
    {"name": "lilo_list_local_models", "source_package": "lilo", "tags": ["core", "ollama"], "complexity": "low",
     "description": "Lista modelos Ollama instalados localmente (`ollama list`). Retorna nome, tag, tamanho."},
]


def get_full_registry() -> dict:
    """Retorna registry com as 16 skills CORE injetadas no inicio + as 199 geradas.
    Usar esta funcao no dashboard em vez de carregar registry.json diretamente,
    para garantir que /lilo_chat, /prism_analyze etc apareçam no menu."""
    base = _load_registry()
    base_skills = base.get("skills", [])
    # Evita duplicatas se o usuario regerar o registry com nomes core
    existing = {s["name"] for s in base_skills}
    core = [m for m in _CORE_SKILL_META if m["name"] not in existing]
    return {
        **base,
        "skills": core + base_skills,
        "total_skills": len(core) + len(base_skills),
        "core_skills": len(core),
    }


def list_available_skills(tags: list[str] = None) -> list[dict]:
    """Lista skills disponíveis com metadados."""
    registry = _load_registry()
    skills = registry.get("skills", [])
    if tags:
        skills = [s for s in skills if any(t in s.get("tags", []) for t in tags)]
    return [{"name": s["name"], "package": s["source_package"],
             "tags": s["tags"], "complexity": s["complexity"]}
            for s in skills]
