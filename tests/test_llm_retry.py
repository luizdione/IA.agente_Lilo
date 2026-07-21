"""V16 QW4 -- retry/backoff transitorio centralizado no LLMClient.chat().

Cobre a classificacao de erro (_is_retryable) e o loop de retry em chat()
sem tocar a rede: monkeypatcha _dispatch_chat e zera o backoff.
"""

import requests
import pytest

import shared.llm_client as L


def _http(status_code):
    """Fabrica um requests.HTTPError com .response.status_code."""
    exc = requests.HTTPError()

    class _R:
        pass

    r = _R()
    r.status_code = status_code
    exc.response = r
    return exc


@pytest.mark.parametrize(
    "exc, expected",
    [
        (requests.Timeout(), True),
        (requests.ConnectionError(), True),
        (_http(429), True),
        (_http(500), True),
        (_http(503), True),
        (_http(400), False),
        (_http(401), False),
        (_http(404), False),
        (ValueError("x"), False),
    ],
)
def test_is_retryable(exc, expected):
    assert L._is_retryable(exc) is expected


@pytest.fixture
def fast_retry(monkeypatch):
    """RETRIES=2, backoff=0 -> ate 3 tentativas, sem dormir."""
    monkeypatch.setattr(L, "LLM_RETRIES", 2)
    monkeypatch.setattr(L, "LLM_BACKOFF", 0.0)
    return L.get_client()


def test_retry_transient_then_success(fast_retry, monkeypatch):
    calls = {"n": 0}

    def disp(*a, **k):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise _http(503)
        return "ok"

    monkeypatch.setattr(fast_retry, "_dispatch_chat", disp)
    assert fast_retry.chat("x") == "ok"
    assert calls["n"] == 3  # 1 + 2 retries


def test_4xx_fails_fast(fast_retry, monkeypatch):
    calls = {"n": 0}

    def disp(*a, **k):
        calls["n"] += 1
        raise _http(400)

    monkeypatch.setattr(fast_retry, "_dispatch_chat", disp)
    with pytest.raises(requests.HTTPError):
        fast_retry.chat("x")
    assert calls["n"] == 1  # sem retry em 4xx


def test_transient_exhausts_then_raises(fast_retry, monkeypatch):
    calls = {"n": 0}

    def disp(*a, **k):
        calls["n"] += 1
        raise requests.Timeout()

    monkeypatch.setattr(fast_retry, "_dispatch_chat", disp)
    with pytest.raises(requests.Timeout):
        fast_retry.chat("x")
    assert calls["n"] == 3  # esgota RETRIES+1
