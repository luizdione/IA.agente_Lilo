"""Testes da v13.3: esquecer, listagens, lilo -c <id>, cores."""
import pytest

import lilo.cliente as cliente_mod
from lilo import cli, cores, memoria, sessoes, tools
from lilo.portao import Permissoes
from tests.conftest import FakeOllama, resposta_texto


@pytest.fixture(autouse=True)
def _isolado(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("LILO_SESSIONS_DB", str(tmp_path / "s.db"))
    monkeypatch.setattr(memoria, "_embed", lambda t: None)


def _livre(kind, preview):
    raise AssertionError("tool livre nao confirma")


# --- esquecer ---------------------------------------------------------------
def test_esquecer_apaga_e_e_idempotente():
    perms = Permissoes(modo="ask")
    tools.executar_tool("memorizar", {"chave": "x", "valor": "1"}, perms, _livre)
    assert tools.executar_tool("esquecer", {"chave": "x"},
                               perms, _livre).startswith("[OK]")
    assert "(nada" in tools.executar_tool("lembrar", {"busca": "x"},
                                          perms, _livre)
    assert "(nada" in tools.executar_tool("esquecer", {"chave": "x"},
                                          perms, _livre)


# --- listagens --------------------------------------------------------------
def test_memoria_listar_recentes():
    memoria.gravar("a", "1")
    memoria.gravar("b", "2")
    chaves = [c for c, _, _ in memoria.listar()]
    assert set(chaves) == {"a", "b"}


def test_sessoes_listar_ordenado():
    c1 = sessoes.nova_sessao()
    sessoes.gravar(c1, [{"role": "user", "content": "primeira conversa"}])
    c2 = sessoes.nova_sessao()
    sessoes.gravar(c2, [{"role": "user", "content": "segunda conversa"}])
    linhas = sessoes.listar()
    assert linhas[0][0] == c2 and linhas[1][0] == c1
    assert linhas[0][1] == "segunda conversa"


# --- lilo -c <id> -----------------------------------------------------------
def test_retomar_sessao_especifica(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LILO_ALLOW", str(tmp_path))
    monkeypatch.setenv("LILO_MODE", "auto")
    monkeypatch.setenv("LILO_STREAM", "0")
    monkeypatch.chdir(tmp_path)
    alvo = sessoes.nova_sessao()
    sessoes.gravar(alvo, [{"role": "system", "content": "s"},
                          {"role": "user", "content": "fato_unico_842"}])
    outra = sessoes.nova_sessao()
    sessoes.gravar(outra, [{"role": "system", "content": "s"},
                           {"role": "user", "content": "outra conversa"}])

    fake = FakeOllama([resposta_texto("continuando")])
    monkeypatch.setattr(cliente_mod, "_transport_requests", fake)
    rc = cli.main(["-c", alvo, "continue"])
    assert rc == 0
    assert "retomada" in capsys.readouterr().out
    # o historico ENVIADO ao modelo contem a sessao alvo, nao a outra
    enviado = " ".join(m.get("content", "")
                       for m in fake.chamadas[0][1]["messages"])
    assert "fato_unico_842" in enviado
    assert "outra conversa" not in enviado


# --- cores ------------------------------------------------------------------
def test_cores_desligam_sem_tty(monkeypatch):
    monkeypatch.setenv("LILO_CORES", "1")
    monkeypatch.setattr(cores.sys, "stdout",
                        type("S", (), {"isatty": lambda self: False})())
    assert cores.pinta("oi", "verde") == "oi"


def test_cores_pintam_com_tty(monkeypatch):
    monkeypatch.setenv("LILO_CORES", "1")
    monkeypatch.setattr(cores.sys, "stdout",
                        type("S", (), {"isatty": lambda self: True})())
    assert "\x1b[32m" in cores.pinta("oi", "verde")
    assert cores.pinta_diff("+novo").startswith("\x1b[32m")
    assert cores.pinta_diff("-velho").startswith("\x1b[31m")
    monkeypatch.setenv("LILO_CORES", "0")
    assert cores.pinta("oi", "verde") == "oi"  # kill-switch vence o tty
