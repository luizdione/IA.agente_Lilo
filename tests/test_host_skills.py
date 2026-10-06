"""Skills do Claude lidas no lugar: catalogo, filtro, leitura e scripts (raizes de teste)."""
from __future__ import annotations

import pytest

from lilo_host import skills


def _skill(pasta, nome, descricao, corpo="# Roteiro\nFaca X.", dobrada=False):
    pasta.mkdir(parents=True)
    desc = (">-\n  " + descricao.replace(". ", ".\n  ")) if dobrada else descricao
    (pasta / "SKILL.md").write_text("---\nname: %s\ndescription: %s\n---\n%s\n" % (nome, desc, corpo),
                                    encoding="utf-8")


@pytest.fixture
def raizes(tmp_path, monkeypatch):
    s, b, p = tmp_path / "skills", tmp_path / "skills_bioinfo", tmp_path / "plugins"
    _skill(s / "git_dione", "git_dione", "Publica no GitHub só o cálculo genético. Repositório privado.", dobrada=True)
    (s / "git_dione" / "sync.py").write_text("import sys; print('sync', sys.argv[1:])", encoding="utf-8")
    _skill(s / "perfil_dados", "perfil_dados", "Perfila CSV e Excel grandes sem despejar no contexto.")
    _skill(b / "rnaseq-bulk" / "deseq2", "bio-rnaseq-deseq2", "Differential expression with DESeq2 for bulk RNA-seq.")
    _skill(b / "structural-chem" / "vina", "bio-docking-vina", "Molecular docking with AutoDock Vina.")
    _skill(p / "mk" / "plug" / "skills" / "qpcr", "qpcr-analise", "Analisa Ct de qPCR.")
    (s / "node_modules" / "x").mkdir(parents=True)
    _skill(s / "node_modules" / "x" / "lixo", "lixo", "nao deve aparecer")
    monkeypatch.setenv("LILO_SKILLS_RAIZES", "%s;%s;%s" % (s, b, p))
    skills.catalogo(forcar=True)
    yield
    monkeypatch.delenv("LILO_SKILLS_RAIZES")
    skills._cache.update(itens={}, assinatura=None)


def test_frontmatter_dobrado():
    fm = skills.frontmatter("---\nname: a\ndescription: >-\n  linha um.\n  linha dois\nx: 1\n---\ncorpo")
    assert fm == {"name": "a", "description": "linha um. linha dois", "x": "1"}
    assert skills.frontmatter("sem cabecalho") == {}


def test_catalogo_e_listar(raizes):
    cat = skills.catalogo()
    assert set(cat) == {"git_dione", "perfil_dados", "bio-rnaseq-deseq2", "bio-docking-vina", "qpcr-analise"}
    assert cat["bio-rnaseq-deseq2"]["dominio"] == "rnaseq-bulk" and cat["qpcr-analise"]["origem"] == "plugins"
    sem = skills.listar()
    assert {s["nome"] for s in sem["skills"]} == {"git_dione", "perfil_dados"}
    assert sem["contagem"] == {"skills": 2, "skills_bioinfo": 2, "plugins": 1}
    com = skills.listar("docking")
    assert [s["nome"] for s in com["skills"]] == ["bio-docking-vina"]
    assert skills.listar("calculo genetico")["skills"][0]["nome"] == "git_dione"   # sem acento tambem acha
    assert skills.listar("qpcr")["skills"][0]["origem"] == "plugins"
    assert skills.listar("nada-disso")["skills"] == []


def test_ler_e_script(raizes):
    t = skills.ler("git_dione")
    assert "Repositório privado" in t and "sync.py" in t and "Faca X." in t
    assert skills.ler("perfil_dados").startswith("[skill perfil_dados")
    assert skills.ler("inexistente").startswith("[ERRO]")
    s = skills.script("git_dione", "sync.py")
    assert s.name == "sync.py"
    assert skills.script("git_dione", "../perfil_dados/SKILL.md").startswith("[ERRO]")
    assert skills.script("git_dione", "nao.py").startswith("[ERRO]")
    assert skills.pasta("git_dione").name == "git_dione"
