"""tests/shared/test_mcp_client.py — V18.6 E6: cliente MCP (offline).

Sem servidor MCP e SEM o pacote `mcp` instalado (o subconjunto de CI nao o
tem — e esse e o cenario que precisa degradar com elegancia). Cobre: parsing
da allow-list dupla, mensagens de barra (servidor/tool nao permitidos),
degradacao quando `mcp` esta ausente e o handler MCP em lilo.
"""
from __future__ import annotations

import shared.mcp_client as mc


def _cfg(monkeypatch, tmp_path, texto: str):
    p = tmp_path / "clients.yaml"
    p.write_text(texto, encoding="utf-8")
    monkeypatch.setattr(mc, "CLIENTS_CONFIG", p)


def test_list_servers_le_allowlist(monkeypatch, tmp_path):
    _cfg(monkeypatch, tmp_path, """
servers:
  fs:
    enabled: true
    command: npx
    args: ["-y", "server-fs"]
    tools: ["read_file"]
  desligado:
    enabled: false
    command: uvx
""")
    servers = {s["server"]: s for s in mc.list_servers()}
    assert servers["fs"]["enabled"] is True
    assert servers["fs"]["tools"] == ["read_file"]
    assert servers["desligado"]["enabled"] is False


def test_servidor_fora_da_allowlist(monkeypatch, tmp_path):
    _cfg(monkeypatch, tmp_path, "servers: {}\n")
    out = mc.call_tool("inexistente", "x", {})
    assert "nao esta na allow-list" in out


def test_servidor_desabilitado(monkeypatch, tmp_path):
    _cfg(monkeypatch, tmp_path, """
servers:
  fs:
    enabled: false
    command: npx
""")
    assert "enabled: false" in mc.call_tool("fs", "read_file", {})


def test_tool_fora_da_allowlist(monkeypatch, tmp_path):
    _cfg(monkeypatch, tmp_path, """
servers:
  fs:
    enabled: true
    command: npx
    tools: ["read_file"]
""")
    out = mc.call_tool("fs", "delete_everything", {})
    assert "fora da allow-list" in out


def test_degradacao_sem_pacote_mcp(monkeypatch, tmp_path):
    # servidor+tool VALIDOS, mas pacote 'mcp' ausente -> mensagem clara, sem crash
    _cfg(monkeypatch, tmp_path, """
servers:
  fs:
    enabled: true
    command: npx
    tools: null
""")
    monkeypatch.setattr(mc, "_mcp_available",
                        lambda: (False, "[mcp] pacote 'mcp' nao instalado"))
    out = mc.call_tool("fs", "qualquer", {"a": 1})
    assert "nao instalado" in out


def test_handler_mcp_list_servers_vazio(monkeypatch, tmp_path):
    _cfg(monkeypatch, tmp_path, "servers: {}\n")
    from lilo import handle_tool_call
    out = handle_tool_call("mcp_list_servers", {})
    assert "nenhum servidor" in out.lower()


def test_handler_mcp_call_valida_args(monkeypatch, tmp_path):
    from lilo import handle_tool_call
    assert "server" in handle_tool_call("mcp_call", {"tool": "x"}).lower()
    assert "tool" in handle_tool_call("mcp_call", {"server": "fs"}).lower()
