"""Grupo codigo: arquivos (ler/escrever/editar/buscar/listar), raizes de escrita e protegidos."""
from __future__ import annotations

import os

import pytest

from lilo_host import arquivos, comum


@pytest.fixture(autouse=True)
def _raizes(tmp_path, monkeypatch):
    monkeypatch.setattr(comum, "RAIZES", [tmp_path])
    monkeypatch.setattr(comum, "TRABALHO", tmp_path)
    yield


def test_ler_paginacao_numeracao_e_crlf(tmp_path):
    arq = tmp_path / "a.txt"
    arq.write_bytes(b"l1\r\nl2\r\nl3\r\nl4\r\n")
    r = arquivos.ler(str(arq), inicio=2, linhas=2)
    assert r.startswith("[ok]") and "linhas 2-3 de 4" in r and "2\tl2\n3\tl3" in r and "inicio=4" in r
    assert arquivos.ler(str(arq), inicio=9).startswith("[ERRO]")
    r2 = arquivos.ler(str(arq))
    assert r2.endswith("4\tl4") and "para continuar" not in r2
    assert "nao existe" in arquivos.ler(str(tmp_path / "nada.txt"))


def test_ler_binario_protegido_e_latin1(tmp_path):
    (tmp_path / "b.png").write_bytes(b"\x89PNG\x00\x00")
    assert "binario" in arquivos.ler(str(tmp_path / "b.png"))
    (tmp_path / "c.dat").write_bytes(bytes(range(256)) * 4)
    assert "binario" in arquivos.ler(str(tmp_path / "c.dat"))
    (tmp_path / ".env").write_text("SEGREDO=1", encoding="utf-8")
    assert "protegido" in arquivos.ler(str(tmp_path / ".env"))
    (tmp_path / "chave.pem").write_text("x", encoding="utf-8")
    assert "protegido" in arquivos.ler(str(tmp_path / "chave.pem"))
    (tmp_path / "l1.txt").write_bytes("ação".encode("latin-1"))
    assert "ação" in arquivos.ler(str(tmp_path / "l1.txt"))


def test_ler_teto_de_caracteres_e_linha_longa(tmp_path):
    arq = tmp_path / "g.txt"
    arq.write_text("\n".join("x" * 100 for _ in range(400)), encoding="utf-8")
    r = arquivos.ler(str(arq), linhas=400)
    # teto ~16k no corpo (cabecalho com o caminho e a ultima linha ficam fora da conta)
    assert "para continuar: inicio=" in r and len(r) < arquivos.LER_MAX_CHARS + 1000
    (tmp_path / "longa.txt").write_text("y" * 3000, encoding="utf-8")
    assert "[linha cortada]" in arquivos.ler(str(tmp_path / "longa.txt"))


def test_escrever_cria_pastas_nao_sobrescreve_e_diff(tmp_path):
    alvo = tmp_path / "sub" / "novo.py"
    r = arquivos.escrever(str(alvo), "print(1)\n")
    assert r.startswith("[ok]") and alvo.read_text(encoding="utf-8") == "print(1)\n"
    r2 = arquivos.escrever(str(alvo), "print(2)\n")
    assert r2.startswith("[ERRO]") and "ja existe" in r2 and "arquivo_editar" in r2
    assert alvo.read_text(encoding="utf-8") == "print(1)\n"
    r3 = arquivos.escrever(str(alvo), "print(2)\n", sobrescrever=True)
    assert "-print(1)" in r3 and "+print(2)" in r3
    r4 = arquivos.escrever(str(tmp_path / "ruim.py"), "def x(:\n")
    assert r4.startswith("[ok]") and "[aviso] sintaxe Python: linha 1" in r4


def test_escrever_preserva_crlf(tmp_path):
    arq = tmp_path / "w.txt"
    arq.write_bytes(b"a\r\nb\r\n")
    arquivos.escrever(str(arq), "a\nc\n", sobrescrever=True)
    assert arq.read_bytes() == b"a\r\nc\r\n"
    novo = tmp_path / "n.txt"
    arquivos.escrever(str(novo), "a\nb\n")
    assert novo.read_bytes() == b"a\nb\n"


def test_editar_unico_com_diff_e_crlf(tmp_path):
    arq = tmp_path / "m.py"
    arq.write_bytes(b"def f():\r\n    return 1\r\n")
    r = arquivos.editar(str(arq), "    return 1", "    return 2")
    assert r.startswith("[ok]") and "-    return 1" in r and "+    return 2" in r
    assert arq.read_bytes() == b"def f():\r\n    return 2\r\n"
    r2 = arquivos.editar(str(arq), "return 2", "return (")
    assert "[aviso] sintaxe" in r2


def test_editar_nao_encontrado_ambiguo_todas_e_iguais(tmp_path):
    arq = tmp_path / "e.txt"
    arq.write_text("alfa = 1\nbeta = 2\nalfa = 1\n", encoding="utf-8")
    r = arquivos.editar(str(arq), "alfa = 7", "alfa = 9")
    assert r.startswith("[ERRO]") and "nao encontrado" in r and "linhas parecidas" in r and "1: alfa = 1" in r
    r2 = arquivos.editar(str(arq), "alfa = 1", "alfa = 9")
    assert r2.startswith("[ERRO]") and "2 vezes" in r2 and "linhas 1, 3" in r2
    assert arq.read_text(encoding="utf-8").count("alfa = 1") == 2
    r3 = arquivos.editar(str(arq), "alfa = 1", "alfa = 9", todas=True)
    assert r3.startswith("[ok]") and arq.read_text(encoding="utf-8").count("alfa = 9") == 2
    assert "iguais" in arquivos.editar(str(arq), "beta", "beta")
    assert "vazio" in arquivos.editar(str(arq), "", "x")
    assert "nao existe" in arquivos.editar(str(tmp_path / "nada.txt"), "a", "b")


def test_buscar_literal_regex_glob_contexto_e_limite(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\ntermo_x = 2\ny = 3\n", encoding="utf-8")
    (tmp_path / "src" / "b.md").write_text("termo_x aqui\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "c.py").write_text("termo_x ignorado\n", encoding="utf-8")
    (tmp_path / "img.png").write_bytes(b"termo_x")
    r = arquivos.buscar("termo_x", str(tmp_path))
    assert r.startswith("[ok] 2 resultado") and "a.py:2: termo_x = 2" in r and "b.md:1:" in r
    assert "node_modules" not in r and "img.png" not in r
    r2 = arquivos.buscar("termo_x", str(tmp_path), glob="*.py", contexto=1)
    assert "b.md" not in r2 and "a.py-1- x = 1" in r2 and "a.py-3- y = 3" in r2
    assert "nenhum resultado" in arquivos.buscar("termo.x", str(tmp_path), glob="*.md")   # literal
    assert "b.md:1" in arquivos.buscar("termo.x", str(tmp_path), glob="*.md", regex=True)
    assert "invalida" in arquivos.buscar("(", str(tmp_path), regex=True)
    assert "cortado em 1" in arquivos.buscar("termo_x", str(tmp_path), max_resultados=1)
    assert "nao existe" in arquivos.buscar("x", str(tmp_path / "nada"))
    assert "vazio" in arquivos.buscar("  ", str(tmp_path))


def test_listar_glob_e_limite(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "a.py").write_text("1", encoding="utf-8")
    (tmp_path / "p" / "b.txt").write_text("22", encoding="utf-8")
    (tmp_path / "p" / ".git").mkdir()
    (tmp_path / "p" / ".git" / "HEAD").write_text("x", encoding="utf-8")
    r = arquivos.listar("**/*.py", str(tmp_path / "p"))
    assert r.startswith("[ok] 1 arquivo") and "a.py  (1 B)" in r
    r2 = arquivos.listar("**/*", str(tmp_path / "p"))
    assert "b.txt" in r2 and ".git" not in r2
    assert "cortada em 1" in arquivos.listar("**/*", str(tmp_path / "p"), max_resultados=1)
    assert "nao existe" in arquivos.listar("*", str(tmp_path / "nada"))


def test_raizes_e_protegidos(tmp_path):
    fora = tmp_path.parent / ("fora_" + tmp_path.name + ".txt")
    assert "fora das raizes" in arquivos.escrever(str(fora), "x")
    assert "fora das raizes" in arquivos.escrever(str(tmp_path / ".." / fora.name), "x")
    assert not fora.exists()
    if os.name == "nt":   # no Linux (CI) a barra invertida nao separa: a string vira um nome de arquivo comum
        assert "fora das raizes" in arquivos.escrever(r"\\servidor\share\x.txt", "x")
    assert "fora das raizes" in arquivos.escrever(str(tmp_path / "CON"), "x")
    assert "fora das raizes" in arquivos.escrever(str(tmp_path / "a.txt:fluxo"), "x")
    assert "protegido" in arquivos.escrever(str(tmp_path / ".env"), "x")
    assert arquivos.escrever(str(tmp_path / ".env.example"), "X=").startswith("[ok]")
    (tmp_path / ".git").mkdir()
    assert "protegido" in arquivos.escrever(str(tmp_path / ".git" / "config"), "x")
    assert "protegido" in arquivos.editar(str(tmp_path / "host_token.txt"), "a", "b")
    if os.name == "nt":   # o Windows nao distingue caixa: continua dentro da raiz
        assert arquivos.escrever(os.path.join(str(tmp_path).upper(), "caixa.txt"), "x").startswith("[ok]")


@pytest.mark.skipif(os.name != "nt", reason="juncao e coisa do Windows")
def test_juncao_que_escapa_e_recusada(tmp_path):
    import _winapi
    fora = tmp_path.parent / ("alvo_" + tmp_path.name)
    fora.mkdir()
    link = tmp_path / "atalho"
    try:
        _winapi.CreateJunction(str(fora), str(link))
    except OSError as e:
        pytest.skip("sem juncao: %s" % e)
    assert "fora das raizes" in arquivos.escrever(str(link / "x.txt"), "x")
    assert not (fora / "x.txt").exists()
