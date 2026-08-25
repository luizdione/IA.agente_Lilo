"""Teste de ponta-a-ponta do CLI one-shot (F5) — sem rede, sem stdin."""
import pytest

import lilo.cliente as cliente_mod
from lilo import cli, sessoes
from tests.conftest import FakeOllama, resposta_texto, resposta_tools


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_SESSIONS_DB", str(tmp_path / "s.db"))
    monkeypatch.setenv("LILO_ALLOW", str(tmp_path))
    monkeypatch.setenv("LILO_MODE", "auto")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_one_shot_completo_com_tool_e_persistencia(ambiente, monkeypatch, capsys):
    (ambiente / "x.txt").write_text("valor_42", encoding="utf-8")
    fake = FakeOllama([
        resposta_tools(("ler", {"caminho": str(ambiente / "x.txt")})),
        resposta_texto("O arquivo diz valor_42."),
    ])
    monkeypatch.setattr(cliente_mod, "_transport_requests", fake)

    rc = cli.main(["leia x.txt"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "valor_42" in out
    # a sessao foi persistida com o transcript completo
    msgs = sessoes.carregar_ultima()
    assert msgs is not None
    assert any(m["role"] == "tool" for m in msgs)


def test_one_shot_ollama_off_mensagem_amigavel(ambiente, monkeypatch, capsys):
    import requests

    def explode(url, payload):
        raise requests.ConnectionError("recusada")

    monkeypatch.setattr(cliente_mod, "_transport_requests", explode)
    monkeypatch.setattr(cliente_mod.requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(
                            requests.ConnectionError()))
    rc = cli.main(["oi"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "OFFLINE" in out
