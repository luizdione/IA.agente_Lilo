"""Testes da v13.1: streaming, memoria memorizar/lembrar, tool mcp."""
import pytest

from lilo import memoria, mcp_cliente, tools
from lilo.cliente import ClienteOllama
from lilo.portao import CONFIRMAR, PERMITIR, Permissoes, decidir
from tests.conftest import FakeOllama, resposta_texto


# --- streaming --------------------------------------------------------------
def _chunks_stream():
    return [
        {"message": {"role": "assistant", "content": "Ola"}, "done": False},
        {"message": {"role": "assistant", "content": " mundo"}, "done": False},
        {"message": {"role": "assistant", "content": ""},
         "done": True, "done_reason": "stop"},
    ]


def test_streaming_acumula_e_chama_on_token(monkeypatch):
    monkeypatch.setenv("LILO_STREAM", "1")
    payloads = []

    def stream_fake(url, payload):
        payloads.append(payload)
        return iter(_chunks_stream())

    pedacos = []
    cli = ClienteOllama(transport=FakeOllama([]), stream_transport=stream_fake)
    r = cli.chat([{"role": "user", "content": "x"}],
                 on_token=pedacos.append)
    assert r["content"] == "Ola mundo"
    assert pedacos == ["Ola", " mundo"]
    assert payloads[0]["stream"] is True
    assert r["done_reason"] == "stop"


def test_streaming_com_tool_calls_nos_chunks(monkeypatch):
    monkeypatch.setenv("LILO_STREAM", "1")

    def stream_fake(url, payload):
        return iter([
            {"message": {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "ler", "arguments": {"caminho": "a"}}}]},
             "done": False},
            {"message": {"role": "assistant", "content": ""},
             "done": True, "done_reason": "stop"},
        ])

    cli = ClienteOllama(transport=FakeOllama([]), stream_transport=stream_fake)
    r = cli.chat([{"role": "user", "content": "x"}], on_token=lambda t: None)
    assert r["tool_calls"] == [{"name": "ler", "arguments": {"caminho": "a"}}]
    assert r["message"]["tool_calls"]  # mensagem crua reconstruida p/ historico


def test_stream_desligado_usa_transporte_normal(monkeypatch):
    monkeypatch.setenv("LILO_STREAM", "0")
    fake = FakeOllama([resposta_texto("ok")])

    def stream_nunca(url, payload):
        raise AssertionError("nao deveria usar stream com LILO_STREAM=0")

    cli = ClienteOllama(transport=fake, stream_transport=stream_nunca)
    r = cli.chat([{"role": "user", "content": "x"}], on_token=lambda t: None)
    assert r["content"] == "ok"
    assert fake.chamadas[0][1]["stream"] is False


# --- memoria ----------------------------------------------------------------
@pytest.fixture(autouse=True)
def _memoria_isolada(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "memoria.db"))


def test_memoria_gravar_obter_buscar_apagar():
    memoria.gravar("editor", "PyCharm", tags="preferencias")
    memoria.gravar("editor", "VS Code")  # upsert
    assert memoria.obter("editor") == "VS Code"
    assert memoria.buscar("vs code")[0][0] == "editor"
    assert memoria.apagar("editor") is True
    assert memoria.obter("editor") is None


def test_tools_memorizar_lembrar():
    perms = Permissoes(modo="ask")  # livre: nao pede confirmacao

    def nunca(kind, preview):
        raise AssertionError("memoria e livre — nao confirma")

    assert tools.executar_tool("memorizar", {"chave": "gpu",
                                             "valor": "RTX 3060 12GB"},
                               perms, nunca).startswith("[OK]")
    assert "RTX 3060" in tools.executar_tool("lembrar", {"busca": "gpu"},
                                             perms, nunca)
    assert "RTX 3060" in tools.executar_tool("lembrar", {"chave": "gpu"},
                                             perms, nunca)
    assert "(nada" in tools.executar_tool("lembrar", {"busca": "inexistente"},
                                          perms, nunca)
    assert tools.executar_tool("lembrar", {}, perms, nunca).startswith("[ERRO]")


# --- mcp --------------------------------------------------------------------
def test_mcp_servidores_parse(monkeypatch):
    monkeypatch.setenv("LILO_MCP",
                       "tempo=python -m servidor_tempo; fs=npx -y serv C:\\dados")
    srv = mcp_cliente.servidores()
    assert srv["tempo"] == ["python", "-m", "servidor_tempo"]
    assert srv["fs"][0] == "npx"
    monkeypatch.setenv("LILO_MCP", "")
    assert mcp_cliente.servidores() == {}


def test_mcp_servidor_desconhecido(monkeypatch):
    monkeypatch.setenv("LILO_MCP", "tempo=python -m x")
    saida = mcp_cliente.chamar("nao_existe")
    assert saida.startswith("[ERRO]")
    assert "tempo" in saida  # lista os configurados


def test_tool_mcp_gate_e_execucao(monkeypatch):
    chamadas = []
    monkeypatch.setattr(tools.mcp_cliente, "chamar",
                        lambda s, t="", a=None: chamadas.append((s, t)) or "resultado_mcp")

    # ask: pede confirmacao; 'n' -> NEGADO e nada executa
    perms = Permissoes(modo="ask")
    saida = tools.executar_tool("mcp", {"servidor": "tempo", "tool": "agora"},
                                perms, lambda k, p: "n")
    assert saida.startswith("[NEGADO]") and not chamadas

    # 't' -> grant por kind; proxima chamada nao pergunta
    perguntas = []
    tools.executar_tool("mcp", {"servidor": "tempo", "tool": "agora"},
                        perms, lambda k, p: perguntas.append(k) or "t")
    tools.executar_tool("mcp", {"servidor": "tempo"},
                        perms, lambda k, p: perguntas.append(k) or "t")
    assert perguntas == ["mcp"]
    assert len(chamadas) == 2

    # portao: matriz do kind mcp
    assert decidir("mcp", Permissoes(modo="auto")) == PERMITIR
    assert decidir("mcp", Permissoes(modo="accept_edits")) == CONFIRMAR
