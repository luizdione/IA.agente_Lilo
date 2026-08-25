"""Testes hermeticos do ClienteOllama (F1) — sem rede, via FakeOllama."""
import requests

from lilo.cliente import ClienteOllama, _is_retryable, _normalize_keep_alive
from tests.conftest import FakeOllama, resposta_texto, resposta_tools


def _http_error(code):
    resp = requests.Response()
    resp.status_code = code
    return requests.HTTPError(response=resp)


# --- payload ---------------------------------------------------------------
def test_multi_turno_e_num_ctx(monkeypatch):
    monkeypatch.setenv("LILO_NUM_CTX", "4096")
    fake = FakeOllama([resposta_texto("oi")])
    msgs = [{"role": "system", "content": "s"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "tool", "tool_name": "ler", "content": "r"},
            {"role": "user", "content": "u2"}]
    ClienteOllama(transport=fake).chat(msgs)
    url, payload = fake.chamadas[0]
    assert url.endswith("/api/chat")
    assert payload["messages"] == msgs          # multi-turno VERBATIM
    assert payload["options"]["num_ctx"] == 4096  # sempre explicito
    assert payload["stream"] is False


def test_tools_incluidas_so_quando_passadas():
    fake = FakeOllama([resposta_texto("a"), resposta_texto("b")])
    cli = ClienteOllama(transport=fake)
    cli.chat([{"role": "user", "content": "x"}])
    schemas = [{"type": "function", "function": {"name": "ler"}}]
    cli.chat([{"role": "user", "content": "x"}], tools=schemas)
    assert "tools" not in fake.chamadas[0][1]
    assert fake.chamadas[1][1]["tools"] == schemas


def test_think_desligado_por_default(monkeypatch):
    fake = FakeOllama([resposta_texto("a"), resposta_texto("b")])
    cli = ClienteOllama(transport=fake)
    cli.chat([{"role": "user", "content": "x"}])
    assert fake.chamadas[0][1]["think"] is False  # default: sem monologo
    monkeypatch.setenv("LILO_THINK", "1")
    cli.chat([{"role": "user", "content": "x"}])
    assert "think" not in fake.chamadas[1][1]  # religado: campo ausente


def test_keep_alive_normalizado(monkeypatch):
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "-1")
    fake = FakeOllama([resposta_texto("x")])
    ClienteOllama(transport=fake).chat([{"role": "user", "content": "x"}])
    assert fake.chamadas[0][1]["keep_alive"] == -1  # int, nao "-1"
    assert _normalize_keep_alive("2h") == "2h"


# --- retry -----------------------------------------------------------------
def test_retry_em_erro_transitorio():
    fake = FakeOllama([requests.ConnectionError(), resposta_texto("ok")])
    r = ClienteOllama(transport=fake).chat([{"role": "user", "content": "x"}])
    assert r["content"] == "ok"
    assert len(fake.chamadas) == 2


def test_retry_em_500_fail_fast_em_400():
    fake = FakeOllama([_http_error(500), resposta_texto("ok")])
    assert ClienteOllama(transport=fake).chat(
        [{"role": "user", "content": "x"}])["content"] == "ok"

    fake2 = FakeOllama([_http_error(400)])
    try:
        ClienteOllama(transport=fake2).chat([{"role": "user", "content": "x"}])
        assert False, "400 deveria levantar sem retry"
    except requests.HTTPError:
        pass
    assert len(fake2.chamadas) == 1  # sem retry

    assert _is_retryable(requests.Timeout())
    assert not _is_retryable(ValueError())


# --- parse -----------------------------------------------------------------
def test_fallback_thinking_e_strip():
    fake = FakeOllama([{"message": {"content": "", "thinking": "resposta"},
                        "done_reason": "stop"}])
    assert ClienteOllama(transport=fake).chat(
        [{"role": "user", "content": "x"}])["content"] == "resposta"

    fake2 = FakeOllama([resposta_texto("<thinking>blah</thinking>final")])
    assert ClienteOllama(transport=fake2).chat(
        [{"role": "user", "content": "x"}])["content"] == "final"


def test_tool_calls_normalizados():
    fake = FakeOllama([resposta_tools(("ler", {"caminho": "a.py"}),
                                      ("buscar", '{"padrao": "x"}'),
                                      ("shell", "{{invalido"))])
    r = ClienteOllama(transport=fake).chat([{"role": "user", "content": "x"}])
    tcs = r["tool_calls"]
    assert tcs[0] == {"name": "ler", "arguments": {"caminho": "a.py"}}
    assert tcs[1] == {"name": "buscar", "arguments": {"padrao": "x"}}
    assert tcs[2] == {"name": "shell", "arguments": {}}  # ilegivel -> {}
    # mensagem crua preservada p/ anexar ao historico
    assert r["message"]["tool_calls"][0]["function"]["name"] == "ler"
