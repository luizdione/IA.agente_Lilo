"""Testes da v13.8 — tool `delegar` do mcp-serve (LILO no Claude Code).

`delegar` roda o LOOP inteiro do LILO dentro do servidor MCP — aqui provado
hermeticamente: FakeOllama injetado via monkeypatch de `_criar_cliente`
(padrao _importar_fitz), e o portao do LILO_MCP_SERVE_MODE valendo DENTRO
da tarefa delegada.
"""
from __future__ import annotations

from tests.conftest import FakeOllama, resposta_texto, resposta_tools
from lilo import mcp_servidor
from lilo.cliente import ClienteOllama


def _com_fake(monkeypatch, respostas):
    fake = FakeOllama(respostas)
    monkeypatch.setattr(mcp_servidor, "_criar_cliente",
                        lambda: ClienteOllama(transport=fake))
    return fake


def test_delegar_exposta_e_mcp_continua_fora():
    assert "delegar" in mcp_servidor.WRAPPERS
    assert "mcp" not in mcp_servidor.WRAPPERS
    assert len(mcp_servidor.WRAPPERS) == 11


def test_delegar_devolve_resposta_final(monkeypatch):
    _com_fake(monkeypatch, [resposta_texto("tarefa concluida: 42")])
    assert mcp_servidor.delegar("qual a resposta?") == "tarefa concluida: 42"


def test_delegar_executa_tool_pelo_choke_point(monkeypatch, tmp_path):
    arq = tmp_path / "dado.txt"
    arq.write_text("segredo local 123", encoding="utf-8")
    fake = _com_fake(monkeypatch, [
        resposta_tools(("ler", {"caminho": str(arq)})),
        resposta_texto("o arquivo diz: segredo local 123"),
    ])
    saida = mcp_servidor.delegar("leia %s" % arq)
    assert "segredo local 123" in saida
    # o resultado da tool voltou ao modelo como role=tool (loop de verdade)
    msgs_2a = fake.chamadas[1][1]["messages"]
    assert any(m.get("role") == "tool" and "segredo local 123" in str(m.get("content"))
               for m in msgs_2a)


def test_delegar_respeita_portao_do_serve(monkeypatch):
    # default accept_edits: shell dentro da tarefa delegada vira [NEGADO]
    monkeypatch.delenv("LILO_MCP_SERVE_MODE", raising=False)
    fake = _com_fake(monkeypatch, [
        resposta_tools(("shell", {"comando": "curl x"})),
        resposta_texto("nao rodei o comando"),
    ])
    assert mcp_servidor.delegar("rode curl x") == "nao rodei o comando"
    msgs_2a = fake.chamadas[1][1]["messages"]
    assert any(m.get("role") == "tool" and "[NEGADO]" in str(m.get("content"))
               for m in msgs_2a)


def test_delegar_ancora_no_claude_project_dir(monkeypatch, tmp_path):
    (tmp_path / "LILO.md").write_text("projeto marcador xyz789",
                                      encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    fake = _com_fake(monkeypatch, [resposta_texto("ok")])
    mcp_servidor.delegar("oi")
    system = fake.chamadas[0][1]["messages"][0]
    assert system["role"] == "system"
    assert "xyz789" in system["content"]  # contexto do PROJETO do Claude Code


def test_delegar_modelo_opcional_vai_no_payload(monkeypatch):
    fake = _com_fake(monkeypatch, [resposta_texto("ok")])
    mcp_servidor.delegar("oi", modelo="qwen3:1.7b")
    assert fake.chamadas[0][1]["model"] == "qwen3:1.7b"
