"""Testes da telemetria de economia do MCP (V14.7)."""

import pytest

from shared import metrics, kv_memory


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "kv_metrics.db"
    monkeypatch.setenv("LILO_KV_MEMORY_DB", str(db))
    monkeypatch.setattr(kv_memory, "DB_PATH", db, raising=False)
    monkeypatch.delenv("LILO_MCP_METRICS", raising=False)
    kv_memory.reset_singleton()
    yield
    kv_memory.reset_singleton()


def test_cache_hits_and_misses_aggregate():
    metrics.record_cache("lilo_scholar", hit=False)
    metrics.record_cache("lilo_scholar", hit=True)
    metrics.record_cache("lilo_scholar", hit=True)
    s = metrics.summary(days=1)
    assert s["cache_hits"] == 2
    assert s["cache_misses"] == 1
    assert s["cache_total"] == 3
    assert abs(s["hit_rate"] - (2 / 3)) < 1e-6


def test_budget_savings_aggregate():
    metrics.record_budget("villa_pipeline", 8000)
    metrics.record_budget("villa_pipeline", 2000)
    s = metrics.summary(days=1)
    assert s["budget_truncations"] == 2
    assert s["chars_saved"] == 10000
    assert s["tokens_saved_approx"] == 2500  # 10000 / 4


def test_zero_chars_saved_is_ignored():
    metrics.record_budget("x", 0)
    metrics.record_budget("x", -5)
    s = metrics.summary(days=1)
    assert s["budget_truncations"] == 0
    assert s["chars_saved"] == 0


def test_by_tool_breakdown():
    metrics.record_cache("lilo_web_search", hit=True)
    metrics.record_cache("lilo_web_fetch", hit=False)
    metrics.record_budget("lilo_web_fetch", 1234)
    s = metrics.summary(days=1)
    assert s["by_tool"]["lilo_web_search"]["hits"] == 1
    assert s["by_tool"]["lilo_web_fetch"]["misses"] == 1
    assert s["by_tool"]["lilo_web_fetch"]["chars_saved"] == 1234


def test_metrics_disabled_records_nothing(monkeypatch):
    monkeypatch.setenv("LILO_MCP_METRICS", "0")
    metrics.record_cache("t", hit=True)
    metrics.record_budget("t", 5000)
    s = metrics.summary(days=1)
    assert s["cache_total"] == 0
    assert s["chars_saved"] == 0


def test_empty_summary_safe():
    s = metrics.summary(days=7)
    assert s["hit_rate"] == 0.0
    assert s["tokens_saved_approx"] == 0
    assert s["by_tool"] == {}


def test_recording_never_raises(monkeypatch):
    # Mesmo se a memoria falhar, nao pode propagar excecao.
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(kv_memory, "get_memory", boom)
    metrics.record_cache("t", hit=True)   # nao deve levantar
    metrics.record_budget("t", 10)        # nao deve levantar
