"""tests/shared/test_cost_telemetry.py — V18 QW4/QW5: custo real e latencia.

Offline (sem rede/LLM). Cobre:
  - _anthropic_cost_usd: precos por familia de modelo, cache read/write e o
    fallback fail-safe (modelo desconhecido -> preco Opus, superestima)
  - CostTracker.latency_summary: p50/p95/media do dia (nearest-rank, stdlib)
"""
from __future__ import annotations

from types import SimpleNamespace

from shared.cost_tracker import CostTracker
from shared.llm_client import _anthropic_cost_usd


def _usage(**kw):
    base = dict(input_tokens=0, output_tokens=0,
                cache_creation_input_tokens=0, cache_read_input_tokens=0)
    base.update(kw)
    return SimpleNamespace(**base)


def test_custo_sonnet_input_output():
    # Sonnet: $3/MTok input, $15/MTok output.
    u = _usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(_anthropic_cost_usd("claude-sonnet-4-5", u) - 18.0) < 1e-9


def test_custo_cache_write_e_read():
    # Cache ephemeral (Opus, $5/MTok in): escrita 1.25x, leitura 0.10x.
    u = _usage(cache_creation_input_tokens=1_000_000,
               cache_read_input_tokens=1_000_000)
    esperado = 5.0 * 1.25 + 5.0 * 0.10
    assert abs(_anthropic_cost_usd("claude-opus-4-5", u) - esperado) < 1e-9


def test_modelo_desconhecido_superestima_com_preco_opus():
    u = _usage(input_tokens=1_000_000)
    assert abs(_anthropic_cost_usd("claude-modelo-futuro", u) - 5.0) < 1e-9


def test_usage_sem_campos_de_cache_nao_quebra():
    # SDK antigo pode nao expor cache_*_input_tokens.
    u = SimpleNamespace(input_tokens=100, output_tokens=50)
    assert _anthropic_cost_usd("claude-haiku-4-5", u) > 0


def test_latency_summary_percentis(tmp_path):
    tracker = CostTracker(db_path=tmp_path / "lat.db")
    for ms in (100, 200, 300, 400, 1000):
        tracker.log_request("ollama", "modelo-x", duration_ms=ms)
    lat = tracker.latency_summary()
    assert lat["count"] == 5
    assert lat["p50_ms"] == 300
    assert lat["p95_ms"] == 1000
    assert lat["avg_ms"] == 400


def test_latency_summary_ignora_duration_zero(tmp_path):
    tracker = CostTracker(db_path=tmp_path / "zero.db")
    tracker.log_request("ollama", "m", duration_ms=0)
    tracker.log_request("ollama", "m", duration_ms=500)
    lat = tracker.latency_summary()
    assert lat["count"] == 1 and lat["p50_ms"] == 500


def test_latency_summary_dia_vazio(tmp_path):
    tracker = CostTracker(db_path=tmp_path / "vazio.db")
    lat = tracker.latency_summary()
    assert lat["count"] == 0 and lat["p50_ms"] == 0 and lat["p95_ms"] == 0
