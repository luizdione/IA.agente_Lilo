"""Testes do cache TTL de tools idempotentes (P1, V14.6)."""

import os

import pytest

from shared import mcp_cache, kv_memory


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """DB kv isolado por teste + env limpo.

    DB_PATH e capturado no import de kv_memory, entao so o env nao basta:
    patcheamos o modulo diretamente e zeramos o singleton.
    """
    db = tmp_path / "kv_test.db"
    monkeypatch.setenv("LILO_KV_MEMORY_DB", str(db))
    monkeypatch.setattr(kv_memory, "DB_PATH", db, raising=False)
    monkeypatch.delenv("LILO_MCP_CACHE_TTL", raising=False)
    kv_memory.reset_singleton()
    yield
    kv_memory.reset_singleton()


def _counter_fn():
    """Retorna (fn, calls) -- fn devolve string distinta por contagem."""
    state = {"n": 0}

    def fn(q="", x=1):
        state["n"] += 1
        return f"resultado para {q}/{x} (chamada #{state['n']})"

    return fn, state


def test_cache_hit_avoids_second_call():
    fn, state = _counter_fn()
    out1 = mcp_cache.cached_call("lilo_web_search", fn, ("crispr",), {})
    out2 = mcp_cache.cached_call("lilo_web_search", fn, ("crispr",), {})
    assert state["n"] == 1  # segunda chamada veio do cache
    assert "chamada #1" in out1
    assert "chamada #1" in out2
    assert "LILO cache" in out2  # marcador no hit


def test_different_args_are_separate_entries():
    fn, state = _counter_fn()
    mcp_cache.cached_call("lilo_web_search", fn, ("a",), {})
    mcp_cache.cached_call("lilo_web_search", fn, ("b",), {})
    assert state["n"] == 2


def test_kwargs_part_of_key():
    fn, state = _counter_fn()
    mcp_cache.cached_call("lilo_web_search", fn, (), {"q": "x", "x": 1})
    mcp_cache.cached_call("lilo_web_search", fn, (), {"q": "x", "x": 2})
    assert state["n"] == 2


def test_ttl_zero_disables_cache(monkeypatch):
    monkeypatch.setenv("LILO_MCP_CACHE_TTL", "0")
    fn, state = _counter_fn()
    mcp_cache.cached_call("lilo_web_search", fn, ("q",), {})
    mcp_cache.cached_call("lilo_web_search", fn, ("q",), {})
    assert state["n"] == 2  # sem cache


def test_errors_are_not_cached():
    state = {"n": 0}

    def failing(q=""):
        state["n"] += 1
        return "[ERRO] dial tcp 127.0.0.1:11434: recusou ativamente"

    mcp_cache.cached_call("lilo_scholar", failing, ("q",), {})
    mcp_cache.cached_call("lilo_scholar", failing, ("q",), {})
    assert state["n"] == 2  # erro nao foi cacheado -> chamou de novo


def test_empty_output_not_cached():
    state = {"n": 0}

    def empty(q=""):
        state["n"] += 1
        return "   "

    mcp_cache.cached_call("lilo_scholar", empty, ("q",), {})
    mcp_cache.cached_call("lilo_scholar", empty, ("q",), {})
    assert state["n"] == 2


def test_non_string_output_passthrough_not_cached():
    state = {"n": 0}

    def num(q=""):
        state["n"] += 1
        return 42

    out1 = mcp_cache.cached_call("lilo_scholar", num, ("q",), {})
    out2 = mcp_cache.cached_call("lilo_scholar", num, ("q",), {})
    assert out1 == 42 and out2 == 42
    assert state["n"] == 2  # nao-string nao cacheia


def test_make_key_stable_and_distinct():
    k1 = mcp_cache.make_key("t", ("a",), {"x": 1})
    k2 = mcp_cache.make_key("t", ("a",), {"x": 1})
    k3 = mcp_cache.make_key("t", ("a",), {"x": 2})
    assert k1 == k2 and k1 != k3
    assert k1.startswith("t:")


def test_integration_via_lilo_mcp_budget_wrap():
    """Tool cacheavel decorada: 2a chamada nao reexecuta a fn e respeita o teto."""
    import lilo_mcp as m
    state = {"n": 0}

    def lilo_web_search(query: str = "", max_results: int = 5) -> str:
        state["n"] += 1
        return "L" * 100000  # grande -> deve ser cortado pelo budget tambem

    os.environ["LILO_MCP_MAX_CHARS"] = "2000"
    try:
        w = m._budget_wrap(lilo_web_search)
        o1 = w("crispr")
        o2 = w("crispr")
        assert state["n"] == 1          # cache evitou 2a execucao
        assert len(o1) <= 2000          # budget cortou
        assert len(o2) <= 2000
    finally:
        del os.environ["LILO_MCP_MAX_CHARS"]
