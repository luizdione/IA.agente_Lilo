"""
scripts/smoke_test_v11.py -- Smoke test das mudancas v11 (2026-05-12)
======================================================================
Valida sintaxe, imports, KV memory, cost tracker, detect_domain, etc.
2026-05-12: hotfix detect_domain + CostTracker isolado; novos testes
            para V1 cache LRU, V2 telemetria, V6 domains YAML, V7 explain_routing.
"""

import sys
import ast
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILED = []
PASSED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f"  OK  {name}", flush=True)
    except Exception as e:
        FAILED.append((name, e))
        print(f"  FAIL {name}: {type(e).__name__}: {e}", flush=True)


def test_syntax():
    files = [
        "lilo.py", "lilo_mcp.py", "lilo_api.py",
        "agents/villa_lobos/agent.py",
        "shared/llm_client.py", "shared/policy.py",
        "shared/cost_tracker.py", "shared/kv_memory.py",
    ]
    for rel in files:
        p = ROOT / rel
        if not p.exists():
            raise FileNotFoundError(rel)
        ast.parse(p.read_text(encoding="utf-8"))


def test_kv_memory():
    import gc, os
    from shared.kv_memory import KVMemory
    fd, path = tempfile.mkstemp(suffix=".db", prefix="lilo_kvtest_")
    os.close(fd)
    try:
        m = KVMemory(db_path=Path(path))
        m.set("k1", "hello", ns="test")
        m.set("k2", {"x": [1, 2, 3]}, ns="test", tags="api,conf")
        assert m.get("k1", ns="test") == "hello"
        assert m.get("k2", ns="test")["x"] == [1, 2, 3]
        assert len(m.list(ns="test")) == 2
        assert len(m.list(ns="test", tag="api")) == 1
        assert m.delete("k1", ns="test") is True
        assert m.delete("k1", ns="test") is False
        assert len(m.list(ns="test")) == 1
        del m
        gc.collect()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_cost_tracker():
    """Isola CostTracker em tempfile para evitar 'disk I/O error' quando
    rodando em ambiente sandbox onde o path padrao nao tem write."""
    import os
    from shared.cost_tracker import CostTracker
    fd, path = tempfile.mkstemp(suffix=".db", prefix="lilo_costtest_")
    os.close(fd)
    try:
        t = CostTracker(db_path=Path(path))
        t.log_request(
            backend="ollama", model="llama3.1:8b",
            subagent="smoke_test", tier="ollama",
            cost_usd=0.0, query_preview="smoke test", duration_ms=10,
        )
        s = t.daily_summary()
        assert s["total_requests"] >= 1
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_detect_domain():
    from agents.villa_lobos.agent import _detect_domain, DOMAIN_KEYWORDS
    assert _detect_domain("rodar ANOVA no exp1.xlsx") == "prism"
    assert _detect_domain("SELECT count(*) from genomas") == "sql"
    assert _detect_domain("sumarize o pdf paper.pdf") == "pdf"
    assert _detect_domain("buscar artigos PubMed sobre TcTR") == "scholar"
    assert _detect_domain("quanto e 2+2") is None
    core_domains = {"prism", "sql", "pdf", "scholar"}
    keys = set(DOMAIN_KEYWORDS.keys())
    assert core_domains.issubset(keys), \
        f"core domains ausentes: {core_domains - keys}"


def test_lilo_imports():
    import lilo
    assert callable(lilo.route)
    assert callable(lilo.handle_tool_call)
    assert callable(lilo.list_all_tools)


def test_villa_lobos_import():
    from agents.villa_lobos.agent import VillaLobosAgent
    a = VillaLobosAgent()
    assert hasattr(a, "_route_via_llm")
    assert hasattr(a, "_delegate_to_specialist")
    assert hasattr(a, "run")


def test_lilo_mcp_import():
    import importlib
    spec = importlib.util.spec_from_file_location("_lmcp", ROOT / "lilo_mcp.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        for tool in ("lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
                     "lilo_memory_delete", "lilo_cost_today", "lilo_cost_recent"):
            assert hasattr(mod, tool), f"missing tool: {tool}"
    except ImportError as e:
        if "mcp" in str(e):
            print("    (mcp pkg ausente; pulando)")
            return
        raise


def test_lilo_api_optional():
    try:
        import fastapi  # noqa
    except ImportError:
        print("    (fastapi nao instalado; pulando)")
        return
    import importlib
    spec = importlib.util.spec_from_file_location("_lapi", ROOT / "lilo_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "app")



# ----------------------------------------------------------------------
# 2026-05-12: novos testes para Sprint 2 do Villa_Lobos
# ----------------------------------------------------------------------

def test_v1_cache_lru():
    """V1: _orchestrate_decision deve fazer cache hit em queries identicas."""
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    s0 = v.cache_stats()
    assert s0["hits"] == 0 and s0["misses"] == 0, "estado inicial sujo"
    d1 = v._orchestrate_decision("o que e PCR")
    d2 = v._orchestrate_decision("  O  QUE  E  PCR  ")  # normalizada -> hit
    s = v.cache_stats()
    assert s["hits"] >= 1, f"esperado >=1 hit, ficou {s}"
    assert d1.get("complexity") == d2.get("complexity"), "decisao divergiu"
    assert "_source" in d1, "decision deve expor _source (llm/heuristic/fallback)"


def test_v6_domains_yaml():
    """V6: domains.yaml deve adicionar genomics/proteomics/bioinformatics
    aos defaults sem remover dominios pre-existentes."""
    from agents.villa_lobos.agent import (
        get_domain_keywords, _DOMAIN_DEFAULTS, _detect_domain
    )
    kw = get_domain_keywords()
    # Defaults preservados
    for d in _DOMAIN_DEFAULTS:
        assert d in kw, f"dominio default removido: {d}"
    # Novos dominios cientificos (se YAML presente)
    if (Path(__file__).resolve().parents[1] / "config" / "villa" / "domains.yaml").exists():
        for d in ("genomics", "proteomics", "bioinformatics"):
            assert d in kw, f"YAML deveria adicionar dominio: {d}"
        assert _detect_domain("whole genome variant calling fastq vcf") == "genomics"
        assert _detect_domain("mass spectrometry maxquant proteomic") == "proteomics"


def test_v7_explain_routing():
    """V7: explain_routing retorna decision + delegate + stages sem rodar pipeline."""
    from agents.villa_lobos.agent import VillaLobosAgent
    v = VillaLobosAgent()
    info = v.explain_routing("compare grupos com anova one-way", allow_delegate=True)
    assert "decision" in info and "stages_planned" in info
    assert info["domain_heuristic"] == "prism"
    assert info["stages_planned"][0] == "orchestrator"
    assert info["stages_planned"][-1] == "reporter"
    assert isinstance(info["cache"], dict) and "hits" in info["cache"]


def test_v2_stage_telemetry_schema():
    """V2: cost_tracker.log_request deve aceitar subagent='villa_<role>'
    com duration_ms (smoke do schema, sem chamar LLM)."""
    import os
    from shared.cost_tracker import CostTracker
    fd, path = tempfile.mkstemp(suffix=".db", prefix="lilo_v2test_")
    os.close(fd)
    try:
        t = CostTracker(db_path=Path(path))
        for role in ("orchestrator", "planner", "reader", "worker", "reporter"):
            t.log_request(
                backend="ollama", model="llama3.1:8b",
                subagent=f"villa_{role}", tier="ollama_fast",
                query_preview=f"[{role}] smoke", duration_ms=42,
            )
        recent = t.recent_requests(limit=10)
        subs = [r["subagent"] for r in recent]
        assert any(s.startswith("villa_") for s in subs),             f"subagent stage-level ausente: {subs}"
        # duration_ms tem que estar gravado
        assert any(r.get("duration_ms") == 42 for r in recent)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_claude_code_profile():
    """profile 'claude_code' deve existir e ser enxuto (sem fs_*, sem run_*)."""
    import importlib
    spec = importlib.util.spec_from_file_location("_lmcp_cc", ROOT / "lilo_mcp.py")
    mod = importlib.util.module_from_spec(spec)
    # Forcar profile via env
    import os
    prev = os.environ.get("LILO_MCP_PROFILE")
    os.environ["LILO_MCP_PROFILE"] = "claude_code"
    try:
        try:
            spec.loader.exec_module(mod)
        except ImportError as e:
            if "mcp" in str(e):
                print("    (mcp pkg ausente; pulando)")
                return
            raise
        allowed = mod._PROFILE_TOOLS.get("claude_code")
        assert allowed is not None and isinstance(allowed, set),             "profile claude_code ausente"
        # nao deve ter ferramentas redundantes com o CLI nativo
        for redundant in ("fs_read", "fs_write", "run_shell", "run_python",
                          "lilo_chat"):
            assert redundant not in allowed,                 f"profile enxuto nao deveria expor {redundant}"
        # deve ter os complementares
        for needed in ("villa_pipeline", "villa_explain_routing", "lilo_scholar",
                       "prism_analyze", "lilo_memory_get"):
            assert needed in allowed, f"profile claude_code sem {needed}"
    finally:
        if prev is None:
            os.environ.pop("LILO_MCP_PROFILE", None)
        else:
            os.environ["LILO_MCP_PROFILE"] = prev



def main():
    print("=" * 60, flush=True)
    print("LILO smoke test v11 (2026-05-12 -- Sprint 2)", flush=True)
    print("=" * 60, flush=True)
    check("01 sintaxe (.py)", test_syntax)
    check("02 KVMemory (set/get/list/delete)", test_kv_memory)
    check("03 CostTracker", test_cost_tracker)
    check("04 Villa _detect_domain heuristica", test_detect_domain)
    check("05 lilo.py imports", test_lilo_imports)
    check("06 VillaLobosAgent imports", test_villa_lobos_import)
    check("07 lilo_mcp.py imports + tools", test_lilo_mcp_import)
    check("08 lilo_api.py imports (opcional)", test_lilo_api_optional)
    check("09 V1 cache LRU em _orchestrate_decision", test_v1_cache_lru)
    check("10 V2 telemetria stage-level (schema)", test_v2_stage_telemetry_schema)
    check("11 V6 domain registry pluggable (YAML)", test_v6_domains_yaml)
    check("12 V7 explain_routing (debug sem pipeline)", test_v7_explain_routing)
    check("13 profile claude_code enxuto", test_claude_code_profile)
    print("=" * 60, flush=True)
    print(f"PASSOU: {len(PASSED)} | FALHOU: {len(FAILED)}", flush=True)
    if FAILED:
        for n, e in FAILED:
            print(f"  - {n}: {e}", flush=True)
        sys.exit(1)
    print("OK -- todas as verificacoes passaram.", flush=True)


if __name__ == "__main__":
    main()
