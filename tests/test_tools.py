"""Testes das tools e do choke-point executar_tool (F2+F3). Hermeticos."""
import os
import sys
import time

import pytest

from lilo import tools
from lilo.portao import Permissoes

AUTO = Permissoes(modo="auto")


def _auto():
    return Permissoes(modo="auto")


def _nunca_confirma(kind, preview):
    raise AssertionError("nao deveria pedir confirmacao aqui")


def run(nome, args, perms=None, confirmar=_nunca_confirma):
    return tools.executar_tool(nome, args, perms or _auto(), confirmar)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Allow-list apontada p/ tmp_path; cwd tambem."""
    monkeypatch.setenv("LILO_ALLOW", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- ler --------------------------------------------------------------------
def test_ler_numerado_offset_limite(sandbox):
    arq = sandbox / "a.txt"
    arq.write_text("um\ndois\ntres\nquatro\n", encoding="utf-8")
    assert run("ler", {"caminho": str(arq)}).startswith("1→um")
    parcial = run("ler", {"caminho": str(arq), "offset": 2, "limite": 2})
    assert parcial.splitlines()[0] == "2→dois"
    assert "3→tres" in parcial
    assert "use offset=4" in parcial


def test_ler_binario_recusa(sandbox):
    arq = sandbox / "b.bin"
    arq.write_bytes(b"\x00\x01\x02abc")
    assert run("ler", {"caminho": str(arq)}).startswith("[ERRO] arquivo binario")


def test_ler_inexistente(sandbox):
    assert run("ler", {"caminho": str(sandbox / "x.txt")}).startswith("[ERRO]")


# --- escrever / editar ------------------------------------------------------
def test_escrever_atomico_e_editar_unico(sandbox):
    arq = sandbox / "c.py"
    assert run("escrever", {"caminho": str(arq),
                            "conteudo": "x = 1\ny = 2\n"}).startswith("[OK]")
    assert arq.read_text() == "x = 1\ny = 2\n"
    assert not list(sandbox.glob("*.lilo_tmp"))  # tmp nao sobra

    assert run("editar", {"caminho": str(arq), "texto_antigo": "y = 2",
                          "texto_novo": "y = 3"}).startswith("[OK]")
    assert arq.read_text() == "x = 1\ny = 3\n"


def test_editar_zero_e_multiplas_ocorrencias(sandbox):
    arq = sandbox / "d.txt"
    arq.write_text("a\na\n", encoding="utf-8")
    assert "nao encontrado" in run("editar", {
        "caminho": str(arq), "texto_antigo": "zzz", "texto_novo": "w"})
    assert "nao e unico (2" in run("editar", {
        "caminho": str(arq), "texto_antigo": "a", "texto_novo": "b"})
    assert run("editar", {"caminho": str(arq), "texto_antigo": "a",
                          "texto_novo": "b", "todas": True}).startswith("[OK]")
    assert arq.read_text() == "b\nb\n"


# --- listar / buscar --------------------------------------------------------
def test_listar_pula_skip_dirs(sandbox):
    (sandbox / "src").mkdir()
    (sandbox / "src" / "app.py").write_text("x", encoding="utf-8")
    (sandbox / ".git").mkdir()
    (sandbox / ".git" / "lixo.txt").write_text("x", encoding="utf-8")
    saida = run("listar", {"caminho": str(sandbox), "recursivo": True})
    assert "app.py" in saida
    assert "lixo.txt" not in saida


def test_buscar_ignora_git_e_acha_no_codigo(sandbox):
    (sandbox / "app.py").write_text("segredo_alvo = 1\n", encoding="utf-8")
    (sandbox / ".git").mkdir()
    (sandbox / ".git" / "config").write_text("segredo_alvo\n", encoding="utf-8")
    saida = run("buscar", {"padrao": "segredo_alvo", "raiz": str(sandbox)})
    assert "app.py:1" in saida
    assert ".git" not in saida


# --- shell ------------------------------------------------------------------
def test_shell_exit_e_stdout(sandbox):
    saida = run("shell", {"comando": '%s -c "print(42)"' % sys.executable,
                          "cwd": str(sandbox)})
    assert saida.startswith("[exit=0]")
    assert "42" in saida


def test_shell_timeout_mata_arvore(sandbox):
    ini = time.time()
    saida = run("shell", {"comando": '%s -c "import time; time.sleep(30)"'
                          % sys.executable, "cwd": str(sandbox), "timeout": 1})
    assert "[ERRO] timeout" in saida
    assert time.time() - ini < 15


def test_shell_perigoso_bloqueado_mesmo_em_auto(sandbox):
    saida = run("shell", {"comando": "rm -rf / --no-preserve-root"})
    assert saida.startswith("[BLOQUEADO]")


# --- choke-point ------------------------------------------------------------
def test_tool_desconhecida_e_arg_faltando(sandbox):
    assert run("voar", {}).startswith("[ERRO] tool desconhecida")
    assert "obrigatorio ausente: caminho" in run("ler", {})


def test_confirmacao_negada_vira_negado(sandbox):
    perms = Permissoes(modo="ask")
    saida = tools.executar_tool("escrever", {"caminho": str(sandbox / "e.txt"),
                                             "conteudo": "x"},
                                perms, lambda k, p: "n")
    assert saida.startswith("[NEGADO]")
    assert not (sandbox / "e.txt").exists()


def test_confirmacao_t_registra_grant_e_nao_pergunta_de_novo(sandbox):
    perms = Permissoes(modo="ask")
    perguntas = []

    def confirmar(kind, preview):
        perguntas.append(kind)
        return "t"

    a1 = tools.executar_tool("escrever", {"caminho": str(sandbox / "f.txt"),
                                          "conteudo": "1"}, perms, confirmar)
    a2 = tools.executar_tool("escrever", {"caminho": str(sandbox / "g.txt"),
                                          "conteudo": "2"}, perms, confirmar)
    assert a1.startswith("[OK]") and a2.startswith("[OK]")
    assert perguntas == ["write"]  # a 2a nao perguntou (grant por kind)


def test_write_fora_da_allowlist_vira_write_outside(sandbox, tmp_path_factory):
    fora = tmp_path_factory.mktemp("fora") / "x.txt"
    kinds = []

    def confirmar(kind, preview):
        kinds.append(kind)
        return "s"

    perms = Permissoes(modo="accept_edits")  # write dentro passa direto...
    saida = tools.executar_tool("escrever", {"caminho": str(fora),
                                             "conteudo": "x"}, perms, confirmar)
    assert saida.startswith("[OK]")
    assert kinds == ["write_outside"]  # ...fora exige confirmacao


def test_modo_plan_anota_e_nao_executa(sandbox):
    perms = Permissoes(modo="plan")
    saida = tools.executar_tool("escrever", {"caminho": str(sandbox / "h.txt"),
                                             "conteudo": "x"},
                                perms, _nunca_confirma)
    assert saida.startswith("[MODO PLANO]")
    assert not (sandbox / "h.txt").exists()
    assert perms.plano and perms.plano[0][0] == "write"
    # leitura executa normalmente no plan
    (sandbox / "i.txt").write_text("oi", encoding="utf-8")
    assert "1→oi" in tools.executar_tool("ler", {"caminho": str(sandbox / "i.txt")},
                                         perms, _nunca_confirma)


def test_git_write_classificado(sandbox):
    kinds = []
    perms = Permissoes(modo="auto")
    tools.executar_tool("shell", {"comando": "git commit -m teste"},
                        perms, lambda k, p: kinds.append(k) or "n")
    assert kinds == ["git_write"]  # pediu confirmacao MESMO em auto


def test_truncagem_resultado(sandbox):
    arq = sandbox / "grande.txt"
    arq.write_text("A" * 40_000, encoding="utf-8")
    saida = run("ler", {"caminho": str(arq)})
    assert len(saida) <= tools.LIMITE_RESULTADO + 100
    assert "[truncado" in saida


def test_implementacoes_sao_privadas():
    """Regra do CLAUDE.md: nada fora do choke-point. O modulo agente nao
    importa implementacao privada de tool."""
    import inspect

    from lilo import agente
    fonte = inspect.getsource(agente)
    for privada in ("_ler", "_escrever", "_editar", "_shell", "_buscar",
                    "_listar"):
        assert privada not in fonte
    assert os.path.basename(inspect.getfile(agente)) == "agente.py"
