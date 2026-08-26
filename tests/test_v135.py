"""Testes da v13.5: blindagem offline, debug, backup da memoria, REPL."""
import importlib.util
import logging
import sys
from pathlib import Path

import pytest

from lilo import cli, memoria
from lilo.cliente import ClienteOllama
from tests.conftest import FakeOllama, resposta_texto

_spec = importlib.util.spec_from_file_location(
    "smoke_lilo", Path(__file__).resolve().parent.parent / "scripts" /
    "smoke_lilo.py")
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


@pytest.fixture(autouse=True)
def _memoria_isolada(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "m.db"))
    monkeypatch.setattr(memoria, "_embed", lambda t: None)


# --- blindagem offline (o item vermelho) ------------------------------------
def test_candidatos_excluem_cloud_sempre():
    cands, avisos = smoke.montar_candidatos(
        "qwen3:14b",
        ["qwen3:14b", "gpt-oss:120b-cloud", "mistral-large-3:675b-cloud",
         "qwen2.5-coder:14b"],
        ["qwen3:14b", "gpt-oss:120b-cloud", "mistral-large-3:675b-cloud",
         "qwen2.5-coder:14b"])
    assert cands[0] == "qwen3:14b"
    assert all("-cloud" not in c for c in cands)
    assert any("IGNORADOS" in a for a in avisos)


def test_configurado_cloud_e_recusado():
    cands, avisos = smoke.montar_candidatos(
        "gpt-oss:120b-cloud", ["gpt-oss:120b-cloud", "qwen3:4b"],
        ["gpt-oss:120b-cloud", "qwen3:4b"])
    assert cands == ["qwen3:4b"]          # so o local sobra
    assert any("CLOUD" in a for a in avisos)


def test_configurado_ausente_gera_aviso_e_nao_entra():
    cands, avisos = smoke.montar_candidatos(
        "qwen3:14b", ["qwen3:4b"], ["qwen3:4b"])
    assert cands == ["qwen3:4b"]
    assert any("nao esta instalado" in a for a in avisos)


# --- LILO_DEBUG -------------------------------------------------------------
def test_debug_loga_payload_e_resposta(monkeypatch, caplog):
    monkeypatch.setenv("LILO_DEBUG", "1")
    fake = FakeOllama([resposta_texto("oi")])
    with caplog.at_level(logging.DEBUG, logger="lilo.cliente"):
        ClienteOllama(transport=fake).chat(
            [{"role": "user", "content": "marcador_debug_77"}])
    assert "marcador_debug_77" in caplog.text   # payload logado
    assert "resposta:" in caplog.text
    caplog.clear()
    monkeypatch.setenv("LILO_DEBUG", "0")
    fake2 = FakeOllama([resposta_texto("oi")])
    with caplog.at_level(logging.DEBUG, logger="lilo.cliente"):
        ClienteOllama(transport=fake2).chat(
            [{"role": "user", "content": "marcador_debug_88"}])
    assert "marcador_debug_88" not in caplog.text  # desligado nao vaza


# --- backup da memoria ------------------------------------------------------
def test_exportar_importar_roundtrip(tmp_path):
    memoria.gravar("a", "1", tags="t1")
    memoria.gravar("b", "2")
    arq = tmp_path / "backup.json"
    assert memoria.exportar_json(str(arq)) == 2
    memoria.apagar("a")
    memoria.apagar("b")
    assert memoria.listar() == []
    assert memoria.importar_json(str(arq)) == 2
    assert memoria.obter("a") == "1"
    assert dict((c, t) for c, _, t in memoria.listar())["a"] == "t1"


# --- REPL: \esquecer e \atualizar -------------------------------------------
def _sessao_fake(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_SESSIONS_DB", str(tmp_path / "s.db"))
    monkeypatch.chdir(tmp_path)
    return cli.Sessao()


def test_repl_esquecer(tmp_path, monkeypatch, capsys):
    sessao = _sessao_fake(tmp_path, monkeypatch)
    memoria.gravar("x", "1")
    assert cli._comando("\\esquecer x", sessao, cli.UITerminal(), None)
    assert "esquecido: x" in capsys.readouterr().out
    assert memoria.obter("x") is None


def test_repl_atualizar_roda_git_e_pip(tmp_path, monkeypatch, capsys):
    sessao = _sessao_fake(tmp_path, monkeypatch)
    rodados = []

    class R:
        returncode, stdout, stderr = 0, "ok", ""

    monkeypatch.setattr("subprocess.run",
                        lambda c, **k: rodados.append(c) or R())
    cli._comando("\\atualizar", sessao, cli.UITerminal(), None)
    saida = capsys.readouterr().out
    assert rodados[0] == ["git", "pull"]
    assert rodados[1][:4] == [sys.executable, "-m", "pip", "install"]
    assert "atualizado" in saida


def test_repl_memoria_exportar(tmp_path, monkeypatch, capsys):
    sessao = _sessao_fake(tmp_path, monkeypatch)
    memoria.gravar("k", "v")
    destino = tmp_path / "backup.json"
    cli._comando("\\memoria exportar %s" % destino, sessao,
                 cli.UITerminal(), None)
    assert "exportadas 1" in capsys.readouterr().out
    assert destino.exists()
