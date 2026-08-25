"""Testes do portao (F3): matriz modo x kind, grants escopados, git_write."""
from lilo.portao import (CONFIRMAR, PERMITIR, PLANO, Permissoes, decidir,
                         token_comando)


def test_leitura_sempre_livre():
    for modo in ("plan", "ask", "accept_edits", "auto"):
        assert decidir(None, Permissoes(modo=modo)) == PERMITIR


def test_matriz_modos():
    assert decidir("write", Permissoes(modo="auto")) == PERMITIR
    assert decidir("shell", Permissoes(modo="auto")) == PERMITIR
    assert decidir("write", Permissoes(modo="ask")) == CONFIRMAR
    assert decidir("shell", Permissoes(modo="ask")) == CONFIRMAR
    assert decidir("write", Permissoes(modo="accept_edits")) == PERMITIR
    assert decidir("shell", Permissoes(modo="accept_edits")) == CONFIRMAR
    assert decidir("write_outside", Permissoes(modo="accept_edits")) == CONFIRMAR
    assert decidir("write", Permissoes(modo="plan")) == PLANO
    assert decidir("shell", Permissoes(modo="plan")) == PLANO


def test_git_write_sensivel_ate_em_auto():
    """never-commit-unless-asked: auto NAO libera git_write."""
    assert decidir("git_write", Permissoes(modo="auto")) == CONFIRMAR
    assert decidir("git_write", Permissoes(modo="ask")) == CONFIRMAR
    assert decidir("git_write", Permissoes(modo="plan")) == PLANO


def test_grant_por_kind_nao_vaza_para_outro_kind():
    p = Permissoes(modo="ask")
    p.registrar_grant("write")
    assert decidir("write", p) == PERMITIR
    assert decidir("shell", p) == CONFIRMAR          # nao vazou
    assert decidir("write_outside", p) == CONFIRMAR  # nem p/ kind irmao


def test_grant_shell_por_comando_exato():
    p = Permissoes(modo="ask")
    t1 = token_comando("pytest -q")
    p.registrar_grant("shell", t1)
    assert decidir("shell", p, token=t1) == PERMITIR
    assert decidir("shell", p, token=token_comando("rm x")) == CONFIRMAR


def test_grant_git_write_so_por_token():
    p = Permissoes(modo="auto")
    t = token_comando("git commit -m x")
    p.registrar_grant("git_write", t)
    assert decidir("git_write", p, token=t) == PERMITIR
    assert decidir("git_write", p, token=token_comando("git push")) == CONFIRMAR
    # registrar_grant de git_write SEM token nao cria grant por kind
    p2 = Permissoes(modo="ask")
    p2.registrar_grant("git_write")
    assert decidir("git_write", p2) == CONFIRMAR


def test_trocar_modo_valida():
    p = Permissoes()
    assert p.trocar_modo("auto") and p.modo == "auto"
    assert not p.trocar_modo("yolo") and p.modo == "auto"
