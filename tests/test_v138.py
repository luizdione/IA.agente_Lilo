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


# --- v13.12: delegar respeita o interruptor de GPU --------------------------
class _ClienteFalso:
    def __init__(self, no_ar: bool):
        self.no_ar, self.chamou_chat = no_ar, False

    def ping(self):
        return self.no_ar

    def chat(self, *a, **k):
        self.chamou_chat = True
        raise AssertionError("nao deveria chamar o modelo com Ollama offline")


def _sem_ollama(monkeypatch):
    falso = _ClienteFalso(no_ar=False)
    monkeypatch.setattr(mcp_servidor, "_criar_cliente", lambda: falso)
    return falso


def test_delegar_com_ollama_offline_da_mensagem_clara(monkeypatch):
    monkeypatch.delenv("LILO_OLLAMA_SWITCH", raising=False)
    falso = _sem_ollama(monkeypatch)
    saida = mcp_servidor.delegar("faca algo")
    assert saida.startswith("[ERRO]") and "offline" in saida
    assert "ollama serve" in saida
    assert not falso.chamou_chat, "nem tenta rodar o loop"


def test_delegar_avisa_quando_a_gpu_foi_liberada_de_proposito(monkeypatch,
                                                              tmp_path):
    """O dono desliga o Ollama p/ usar a GPU (docking/treino): a resposta tem
    que dizer ISSO, nao um 'offline' generico."""
    switch = tmp_path / "switch.json"
    switch.write_text('{"estado": "desligado", "motivo": "docking rodando"}',
                      encoding="utf-8")
    monkeypatch.setenv("LILO_OLLAMA_SWITCH", str(switch))
    _sem_ollama(monkeypatch)
    saida = mcp_servidor.delegar("faca algo")
    assert "DESLIGADO de proposito" in saida
    assert "docking rodando" in saida
    assert "ollama_ligar" in saida


def test_switch_ligado_ou_ilegivel_nao_atrapalha(monkeypatch, tmp_path):
    monkeypatch.setenv("LILO_OLLAMA_SWITCH", str(tmp_path / "nao_existe.json"))
    assert mcp_servidor._switch_desligado() is None
    ligado = tmp_path / "on.json"
    ligado.write_text('{"estado": "ligado"}', encoding="utf-8")
    monkeypatch.setenv("LILO_OLLAMA_SWITCH", str(ligado))
    assert mcp_servidor._switch_desligado() is None
    lixo = tmp_path / "lixo.json"
    lixo.write_text("nao sou json", encoding="utf-8")
    monkeypatch.setenv("LILO_OLLAMA_SWITCH", str(lixo))
    assert mcp_servidor._switch_desligado() is None


def test_delegar_erro_no_meio_vira_texto_nao_traceback(monkeypatch):
    """Queda de conexao DURANTE a tarefa tambem tem que virar string."""
    monkeypatch.delenv("LILO_OLLAMA_SWITCH", raising=False)

    class Instavel(_ClienteFalso):
        def ping(self):
            return True

    monkeypatch.setattr(mcp_servidor, "_criar_cliente", lambda: Instavel(True))

    def explode(*a, **k):
        raise ConnectionError("conexao caiu no meio")

    from lilo import agente as _agente
    monkeypatch.setattr(_agente, "executar_tarefa", explode)
    saida = mcp_servidor.delegar("faca algo")
    assert saida.startswith("[ERRO]") and "conexao caiu no meio" in saida
