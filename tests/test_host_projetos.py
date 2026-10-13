"""Ponte lilo-host: memoria dos projetos em varias raizes, ate 3 niveis."""
from __future__ import annotations

import pytest

from lilo_host import projetos


def _mem(pasta, nome="PROJECT_STATE.md", texto="# Estado\nconteudo"):
    d = pasta / ".project-memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / nome).write_text(texto, encoding="utf-8")


@pytest.fixture
def raizes(tmp_path, monkeypatch):
    r1, r2 = tmp_path / "r1", tmp_path / "r2"
    _mem(r1 / "p1", texto="# Estado\nTERMO-ALFA no p1")                   # nivel 1
    _mem(r1 / "sub" / "p2", "TASKS.md", "- [ ] tarefa TERMO-ALFA")        # nivel 2
    _mem(r1 / "a" / "b" / "p3")                                          # nivel 3
    _mem(r1 / "a" / "b" / "c" / "p4")                                    # nivel 4: fora
    _mem(r1 / "node_modules" / "px")                                     # ignorado
    (r1 / "p1" / "NEXT_SESSION.md").write_text("handoff", encoding="utf-8")
    _mem(r2 / "p1", texto="outro p1")                                    # colisao de nome
    monkeypatch.setenv("LILO_PROJETOS_RAIZES", "%s;%s;%s" % (r1, r2, tmp_path / "nao_existe"))
    projetos.mapa(forcar=True)
    yield r1, r2
    projetos.mapa(forcar=True)


def test_mapa_profundidade_e_colisao(raizes):
    m = projetos.mapa()
    assert set(m) == {"p1", "sub/p2", "a/b/p3", "p1@r2"}


def test_ler_projeto_inclui_raiz(raizes):
    pj = projetos.ler_projeto("p1")
    assert pj and set(pj.arquivos) == {"PROJECT_STATE.md", "NEXT_SESSION.md"}
    t = pj.texto()
    assert t.index("### PROJECT_STATE.md") < t.index("### NEXT_SESSION.md")
    assert projetos.ler_projeto("nao-existe") is None
    assert "truncado" in pj.texto(max_chars=10)


def test_listar_e_buscar(raizes):
    nomes = {d["nome"] for d in projetos.listar()}
    assert nomes == {"p1", "sub/p2", "a/b/p3", "p1@r2"}
    hits = projetos.buscar("termo-alfa")
    assert {(h["projeto"], h["arquivo"]) for h in hits} == {("p1", "PROJECT_STATE.md"), ("sub/p2", "TASKS.md")}
    assert projetos.buscar("termo-alfa", projeto="sub/p2")[0]["projeto"] == "sub/p2"
    assert projetos.buscar("") == []
