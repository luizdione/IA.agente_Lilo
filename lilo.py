"""
lilo.py — Orquestrador Central LILO
=====================================
Ponto de entrada único que roteia queries para os 4 subagentes:
  - sql     → Analise_SQL/agent.py     (SQL + estatística)
  - pdf     → PDFs_library/agent.py    (sumarização de PDFs)
  - scholar → scholaragent/agent.py    (busca acadêmica)
  - gateway → llm-gateway/agent.py     (chat geral / fallback)

Uso CLI:
    python lilo.py "liste as tabelas disponíveis"
    python lilo.py sql "SELECT COUNT(*) FROM genomas"
    python lilo.py pdf "resumir artigo" --file paper.pdf --mode introduction
    python lilo.py scholar "inibidores de TcTR em bovinos"
    python lilo.py health

Uso como módulo:
    from lilo import route
    resposta = route("buscar artigos sobre docking molecular")
"""

import sys
import argparse
from pathlib import Path

# Garante que o projeto está no path
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.logger import get_logger
from shared.utils import load_env

load_env()
log = get_logger("LILO")

# ── Carregamento lazy dos subagentes ─────────────────────────────────────────
_agents: dict = {}


def _load_agents() -> dict:
    """Inicializa os subagentes (lazy — só carrega quando necessário)."""
    global _agents
    if _agents:
        return _agents

    log.info("Inicializando subagentes LILO...")

    try:
        from Analise_SQL.agent import SQLAgent
        _agents["sql"] = SQLAgent()
        log.info("  ✓ SQLAgent")
    except Exception as e:
        log.warning(f"  ✗ SQLAgent não disponível: {e}")

    try:
        from PDFs_library.agent import PDFAgent
        _agents["pdf"] = PDFAgent()
        log.info("  ✓ PDFAgent")
    except Exception as e:
        log.warning(f"  ✗ PDFAgent não disponível: {e}")

    try:
        from scholaragent.agent import ScholarAgent
        _agents["scholar"] = ScholarAgent()
        log.info("  ✓ ScholarAgent")
    except Exception as e:
        log.warning(f"  ✗ ScholarAgent não disponível: {e}")

    try:
        from llm_gateway.agent import GatewayAgent  # noqa: F401
    except ImportError:
        pass

    try:
        from llm_gateway.agent import GatewayAgent
        _agents["gateway"] = GatewayAgent()
        log.info("  ✓ GatewayAgent")
    except Exception:
        try:
            # Tenta path com hífen (nome da pasta)
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "gateway_agent",
                _ROOT / "llm-gateway" / "agent.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _agents["gateway"] = mod.GatewayAgent()
            log.info("  ✓ GatewayAgent (via path direto)")
        except Exception as e:
            log.warning(f"  ✗ GatewayAgent não disponível: {e}")

    log.info(f"Subagentes carregados: {list(_agents.keys())}")
    return _agents


# ── Roteamento ────────────────────────────────────────────────────────────────

# Mapa de palavras-chave → subagente
_KEYWORD_MAP = {
    "sql":     ["sql", "query", "select", "tabela", "banco", "database",
                "sqlite", "mysql", "estatística", "anova", "t-test"],
    "pdf":     ["pdf", "artigo", "paper", "documento", "arquivo",
                "resumir", "sumarizar", "introdução", "métodos", "doi"],
    "scholar": ["pubmed", "arxiv", "scholar", "literatura", "referência",
                "papers", "publicações", "buscar artigos", "pesquisa acadêmica"],
}


def _detect_tab(query: str) -> str | None:
    """Detecta automaticamente o subagente mais adequado para a query."""
    q = query.lower()
    scores = {tab: 0 for tab in _KEYWORD_MAP}
    for tab, keywords in _KEYWORD_MAP.items():
        for kw in keywords:
            if kw in q:
                scores[tab] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def route(
    query: str,
    tab: str | None = None,
    context: dict | None = None,
) -> str:
    """
    Roteia a query para o subagente correto.

    Args:
        query   — pergunta ou comando do usuário
        tab     — subagente explícito ("sql" | "pdf" | "scholar" | "gateway")
                  Se None, detecção automática por palavras-chave.
        context — dict com informações adicionais (file_path, mode, db_path, etc.)

    Returns:
        Resposta em texto/Markdown do subagente.
    """
    import time
    from shared.policy import get_policy_engine, ExecutionTier
    from shared.cost_tracker import get_tracker

    agents = _load_agents()
    ctx    = context or {}
    policy = get_policy_engine()
    tracker = get_tracker()

    # 0. Parse override (\lilo opus/sonnet/local)
    #    Se houver override, o Policy Engine já trata

    # 1. Tab explícita
    detected = tab
    if not detected:
        detected = _detect_tab(query)

    # 2. Policy Engine decide o tier
    decision = policy.decide(query, context=ctx, subagent=detected or "gateway")
    log.info(f"Policy → tier={decision.tier.value} | model={decision.model} | reason={decision.reason}")

    # 3. No-LLM: executar direto sem modelo
    if decision.tier == ExecutionTier.NO_LLM:
        # Delega ao subagente com flag de execução direta
        ctx["_direct_query"] = True
        ctx["_tier"] = decision.tier.value
        target = detected if detected and detected in agents else "gateway"
        if target in agents:
            t0 = time.time()
            result = agents[target].run(query, ctx)
            tracker.log_request("no_llm", "none", subagent=target, tier=decision.tier.value,
                                query_preview=query[:80], duration_ms=int((time.time()-t0)*1000))
            return result

    # 4. Executar com o tier decidido
    ctx["_tier"] = decision.tier.value
    ctx["_model"] = decision.model
    target = detected if detected and detected in agents else "gateway"

    if target not in agents:
        if "gateway" in agents:
            target = "gateway"
        else:
            return "[LILO] Nenhum subagente disponível. Verifique se Ollama está rodando."

    log.info(f"Roteamento → {target} | tier={decision.tier.value}")

    t0 = time.time()
    try:
        result = agents[target].run(query, ctx)
    except Exception as e:
        # Fallback: escalar tier
        next_tier = policy.get_fallback(decision.tier)
        if next_tier != decision.tier:
            log.warning(f"Fallback: {decision.tier.value} → {next_tier.value} (erro: {e})")
            ctx["_tier"] = next_tier.value
            from shared.policy import TIER_MODELS
            ctx["_model"] = TIER_MODELS.get(next_tier)
            result = agents[target].run(query, ctx)
        else:
            result = f"[LILO] Erro: {e}"

    duration = int((time.time() - t0) * 1000)
    tracker.log_request(
        backend=decision.tier.value,
        model=decision.model or "",
        subagent=target,
        tier=decision.tier.value,
        cost_usd=decision.estimated_cost,
        query_preview=query[:80],
        duration_ms=duration,
    )
    policy.record_cost(decision.estimated_cost)

    # Salvar no Obsidian (se configurado)
    try:
        from shared.obsidian import save_lilo_run
        save_lilo_run(
            query=query, subagent=target, result=result,
            tier=decision.tier.value, model=decision.model or "",
            cost_usd=decision.estimated_cost, duration_ms=duration,
        )
    except Exception:
        pass  # Obsidian é opcional

    return result


def health_check() -> str:
    """Verifica status de todos os subagentes e backends."""
    agents = _load_agents()
    lines = ["## LILO — Status dos Subagentes\n"]

    for name, agent in agents.items():
        try:
            status = agent.health()
            lines.append(f"✅ **{name}**: {status.get('status', 'ok')}")
        except Exception as e:
            lines.append(f"❌ **{name}**: {e}")

    if not agents:
        lines.append("❌ Nenhum subagente carregado.")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="LILO — Orquestrador de subagentes de IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python lilo.py "liste as tabelas disponíveis"
  python lilo.py sql "gere uma query para contar registros por espécie"
  python lilo.py pdf "resumir" --file paper.pdf --mode introduction
  python lilo.py scholar "inibidores TcTR Trypanosoma"
  python lilo.py health
""",
    )
    p.add_argument("tab_or_query", nargs="?", help="Subagente (sql/pdf/scholar/gateway) ou query direta")
    p.add_argument("query", nargs="*",        help="Query (quando tab é especificada)")
    p.add_argument("--file",  "-f",  default="", help="Caminho para arquivo (PDF, SQLite, etc.)")
    p.add_argument("--mode",  "-m",  default="", help="Modo de operação (simple/introduction/methods)")
    p.add_argument("--table", "-t",  default="", help="Nome da tabela SQL")
    return p


def main():
    parser = _build_parser()
    args   = parser.parse_args()

    TABS = {"sql", "pdf", "scholar", "gateway"}

    # Comando especial: health
    if args.tab_or_query == "health":
        print(health_check())
        return

    # Determina tab e query
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

    # Monta contexto
    ctx = {}
    if args.file:
        ctx["file_path"] = args.file
    if args.mode:
        ctx["mode"] = args.mode
    if args.table:
        ctx["table"] = args.table

    print(route(query, tab=tab, context=ctx))


if __name__ == "__main__":
    main()
