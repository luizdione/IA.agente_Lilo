"""Testes da guarda de orcamento de saida do MCP (V14.5)."""

import importlib

import pytest

from shared import mcp_budget


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Garante ambiente limpo (sem overrides de env) por teste."""
    monkeypatch.delenv("LILO_MCP_MAX_CHARS", raising=False)
    monkeypatch.delenv("LILO_MCP_HEAD_RATIO", raising=False)
    yield


def test_small_output_is_noop():
    s = "saida pequena"
    assert mcp_budget.clamp_output(s) is s


def test_non_string_passthrough():
    for v in (123, None, {"a": 1}, [1, 2, 3], 3.14):
        assert mcp_budget.clamp_output(v) is v


def test_large_output_is_truncated(monkeypatch):
    monkeypatch.setenv("LILO_MCP_MAX_CHARS", "1000")
    big = "x" * 5000
    out = mcp_budget.clamp_output(big)
    assert len(out) <= 1000
    assert "LILO truncou" in out


def test_truncation_preserves_head_and_tail(monkeypatch):
    monkeypatch.setenv("LILO_MCP_MAX_CHARS", "2000")
    body = "HEAD_MARKER" + ("m" * 8000) + "TAIL_MARKER"
    out = mcp_budget.clamp_output(body)
    assert out.startswith("HEAD_MARKER")
    assert out.endswith("TAIL_MARKER")
    assert "LILO truncou" in out


def test_zero_budget_disables_guard(monkeypatch):
    monkeypatch.setenv("LILO_MCP_MAX_CHARS", "0")
    big = "y" * 100000
    assert mcp_budget.clamp_output(big) is big


def test_default_budget_passes_typical_outputs():
    # Uma saida tipica (~10k chars) deve passar intacta com o default (48k).
    typical = "linha de resultado\n" * 500  # ~9.5k chars
    assert mcp_budget.clamp_output(typical) is typical


def test_explicit_max_chars_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("LILO_MCP_MAX_CHARS", "100000")
    out = mcp_budget.clamp_output("z" * 5000, max_chars=1000)
    assert len(out) <= 1000


def test_head_ratio_respected(monkeypatch):
    monkeypatch.setenv("LILO_MCP_MAX_CHARS", "3000")
    monkeypatch.setenv("LILO_MCP_HEAD_RATIO", "0.9")
    body = "A" * 10000 + "B" * 10000
    out = mcp_budget.clamp_output(body)
    head = out.split("[...LILO")[0]
    # Com ratio alto, o head domina e e majoritariamente 'A'.
    assert head.count("A") > head.count("B")


def test_budget_wrap_integration():
    """O wrapper do lilo_mcp aplica a guarda e preserva a assinatura."""
    import functools
    import inspect

    from shared.mcp_budget import clamp_output

    def sample(query: str, n: int = 5) -> str:
        """doc da tool."""
        return "w" * 100000

    @functools.wraps(sample)
    def wrapped(*a, **k):
        return clamp_output(sample(*a, **k))

    import os
    os.environ["LILO_MCP_MAX_CHARS"] = "1000"
    try:
        out = wrapped("oi")
        assert len(out) <= 1000
    finally:
        del os.environ["LILO_MCP_MAX_CHARS"]
    # Assinatura preservada (schema MCP intacto).
    sig = inspect.signature(wrapped)
    assert list(sig.parameters) == ["query", "n"]
    assert wrapped.__doc__ == "doc da tool."
