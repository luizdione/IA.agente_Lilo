"""Testes do loop agentico (F2) — FakeOllama roteirizado, sem rede."""
import pytest

from lilo import agente, config
from lilo.cliente import ClienteOllama
from lilo.portao import Permissoes
from tests.conftest import FakeOllama, resposta_texto, resposta_tools


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_ALLOW", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _rodar(fake, tarefa="tarefa", perms=None, ui=None):
    cliente = ClienteOllama(transport=fake)
    msgs = [{"role": "system", "content": "s"}]
    return agente.executar_tarefa(tarefa, msgs, perms or Permissoes(modo="auto"),
                                  cliente=cliente, ui=ui)


def test_fluxo_ler_depois_responder(sandbox):
    (sandbox / "a.txt").write_text("conteudo_x\n", encoding="utf-8")
    fake = FakeOllama([
        resposta_tools(("ler", {"caminho": str(sandbox / "a.txt")})),
        resposta_texto("O arquivo contem conteudo_x."),
    ])
    final, msgs = _rodar(fake)
    assert "conteudo_x" in final
    # historico: system, user, assistant(tool_calls), tool, assistant(final)
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert msgs[3]["tool_name"] == "ler"
    assert "1→conteudo_x" in msgs[3]["content"]
    # a 2a chamada ao modelo recebeu o resultado da tool
    payload2 = fake.chamadas[1][1]
    assert any(m.get("role") == "tool" for m in payload2["messages"])


def test_tool_calls_paralelos_executam_em_ordem(sandbox):
    (sandbox / "um.txt").write_text("1", encoding="utf-8")
    (sandbox / "dois.txt").write_text("2", encoding="utf-8")
    fake = FakeOllama([
        resposta_tools(("ler", {"caminho": str(sandbox / "um.txt")}),
                       ("ler", {"caminho": str(sandbox / "dois.txt")})),
        resposta_texto("ok"),
    ])
    _, msgs = _rodar(fake)
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert len(tool_msgs) == 2
    assert "1→1" in tool_msgs[0]["content"]  # ordem preservada
    assert "1→2" in tool_msgs[1]["content"]


def test_erro_de_tool_volta_ao_modelo_que_corrige(sandbox):
    (sandbox / "b.txt").write_text("oi", encoding="utf-8")
    fake = FakeOllama([
        resposta_tools(("ler", {})),  # sem caminho -> [ERRO]
        resposta_tools(("ler", {"caminho": str(sandbox / "b.txt")})),
        resposta_texto("li"),
    ])
    final, msgs = _rodar(fake)
    assert final == "li"
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert tool_msgs[0]["content"].startswith("[ERRO]")
    assert "1→oi" in tool_msgs[1]["content"]


def test_aborta_apos_3_erros_consecutivos(sandbox):
    fake = FakeOllama([resposta_tools(("ler", {}))] * 3)
    final, _ = _rodar(fake)
    assert final.startswith("[ABORTADO]")
    assert len(fake.chamadas) == 3


def test_teto_de_iteracoes(sandbox, monkeypatch):
    monkeypatch.setenv("LILO_MAX_ITERS", "4")
    (sandbox / "c.txt").write_text("x", encoding="utf-8")
    fake = FakeOllama(
        [resposta_tools(("ler", {"caminho": str(sandbox / "c.txt")}))] * 4)
    final, _ = _rodar(fake)
    assert final.startswith("[LIMITE]")
    assert len(fake.chamadas) == 4


def test_negado_flui_para_o_modelo(sandbox):
    class UINega(agente.UI):
        def confirmar(self, kind, preview):
            return "n"

    fake = FakeOllama([
        resposta_tools(("escrever", {"caminho": str(sandbox / "d.txt"),
                                     "conteudo": "x"})),
        resposta_texto("entendi, nao vou escrever"),
    ])
    final, msgs = _rodar(fake, perms=Permissoes(modo="ask"), ui=UINega())
    assert final == "entendi, nao vou escrever"
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert tool_msgs[0]["content"].startswith("[NEGADO]")
    assert not (sandbox / "d.txt").exists()


def test_tool_como_texto_recebe_nudge_e_refaz(sandbox):
    """Modelo escreve a tool como JSON-texto -> nudge -> refaz nativo."""
    (sandbox / "n.txt").write_text("oi", encoding="utf-8")
    texto_falho = '{"name": "ler", "arguments": {"caminho": "n.txt"}}'
    fake = FakeOllama([
        resposta_texto(texto_falho),
        resposta_tools(("ler", {"caminho": str(sandbox / "n.txt")})),
        resposta_texto("li o arquivo"),
    ])
    final, msgs = _rodar(fake)
    assert final == "li o arquivo"
    assert any(m["role"] == "user" and "TEXTO" in (m.get("content") or "")
               for m in msgs)  # o nudge foi enviado
    assert len(fake.chamadas) == 3


def test_nudge_tem_teto_e_aceita_como_final(sandbox):
    texto_falho = '{"name": "shell", "arguments": {"comando": "x"}}'
    fake = FakeOllama([resposta_texto(texto_falho)] * 3)
    final, _ = _rodar(fake)
    assert final == texto_falho  # apos 2 nudges, vira resposta final
    assert len(fake.chamadas) == 3  # 1 original + 2 re-tentativas


def test_texto_normal_nao_dispara_nudge(sandbox):
    fake = FakeOllama([resposta_texto('a funcao chama-se "name" e recebe '
                                      '"arguments" como parametro')])
    final, _ = _rodar(fake)
    assert len(fake.chamadas) == 1  # sem nome de tool real -> sem nudge


def test_janela_poda_resultados_antigos(monkeypatch):
    monkeypatch.setenv("LILO_NUM_CTX", "2048")
    monkeypatch.setenv("LILO_MAX_TOKENS", "256")
    msgs = [{"role": "system", "content": "s"},
            {"role": "user", "content": "pedido"}]
    for i in range(8):
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"function": {"name": "ler",
                                                  "arguments": {}}}]})
        msgs.append({"role": "tool", "tool_name": "ler",
                     "content": "R%d " % i + "x" * 2000})
    podado = agente.ajustar_janela(msgs)
    assert podado[0]["role"] == "system"          # intocaveis
    assert podado[1]["content"] == "pedido"
    tool_msgs = [m for m in podado if m["role"] == "tool"]
    intactos = [m for m in tool_msgs if not m["content"].startswith(
        "[resultado antigo omitido")]
    assert len(intactos) <= 4                     # so os 4 ultimos intactos
    orcamento = config.num_ctx() - config.max_tokens() - 1024
    assert sum(agente._tok(m) for m in podado) <= orcamento


def test_system_inclui_contexto_do_projeto(tmp_path, monkeypatch):
    (tmp_path / "CLAUDE.md").write_text("# Projeto Zeta\nregra_zeta",
                                        encoding="utf-8")
    sistema = agente.montar_system(tmp_path)
    assert "regra_zeta" in sistema
    assert "DADOS" in sistema  # rotulado como dado, nao instrucao
