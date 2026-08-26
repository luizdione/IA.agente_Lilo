"""Testes da v13.4: LILO como servidor MCP (lilo mcp-serve)."""
import sys

import pytest

from lilo import cli, mcp_servidor, tools


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_ALLOW", str(tmp_path))
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "m.db"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LILO_MCP_SERVE_MODE", raising=False)
    return tmp_path


def test_wrappers_passam_pelo_choke_point(sandbox, monkeypatch):
    chamadas = []
    monkeypatch.setattr(tools, "executar_tool",
                        lambda nome, args, perms, conf: chamadas.append(
                            (nome, args)) or "ok")
    mcp_servidor.ler("a.txt", offset=3)
    mcp_servidor.memorizar("k", "v", tags="t")
    assert chamadas[0] == ("ler", {"caminho": "a.txt", "offset": 3,
                                   "limite": 2000})
    assert chamadas[1] == ("memorizar", {"chave": "k", "valor": "v",
                                         "tags": "t"})
    # a tool mcp NAO e reexposta (proxy de proxy)
    assert "mcp" not in mcp_servidor.WRAPPERS
    assert len(mcp_servidor.WRAPPERS) == 10


def test_default_accept_edits_write_passa_shell_nega(sandbox):
    assert mcp_servidor.escrever(str(sandbox / "x.txt"),
                                 "oi").startswith("[OK]")
    saida = mcp_servidor.shell("echo oi")
    assert saida.startswith("[NEGADO]")
    assert "LILO_MCP_SERVE_MODE=auto" in saida  # dica acionavel


def test_modo_auto_libera_shell_mas_nunca_git(sandbox, monkeypatch):
    monkeypatch.setenv("LILO_MCP_SERVE_MODE", "auto")
    saida = mcp_servidor.shell('%s -c "print(123)"' % sys.executable)
    assert saida.startswith("[exit=0]") and "123" in saida
    assert mcp_servidor.shell("git commit -m x").startswith("[NEGADO]")


def test_cli_roteia_mcp_serve(monkeypatch):
    monkeypatch.setattr(mcp_servidor, "main", lambda: 42)
    assert cli.main(["mcp-serve"]) == 42
