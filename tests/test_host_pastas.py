"""Pastas do host (listar/buscar), repositorios git (listar/executar com deny-list) e scripts."""
from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from lilo_host import execucao, pastas


@pytest.fixture
def arvore(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def soma(a, b):\n    return a + b  # TERMO-X\n", encoding="utf-8")
    (tmp_path / "src" / "b.md").write_text("# Notas\nTermo-x aparece aqui tambem.\n", encoding="utf-8")
    (tmp_path / "dados.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (tmp_path / "node_modules" / "lib").mkdir(parents=True)
    (tmp_path / "node_modules" / "lib" / "c.js").write_text("TERMO-X", encoding="utf-8")
    (tmp_path / "img.png").write_bytes(b"\x89PNG TERMO-X")
    return tmp_path


def test_listar(arvore):
    t = pastas.listar(str(arvore), profundidade=2)
    assert "src/" in t and "a.py" in t and "dados.csv" in t and "node_modules" not in t
    assert "2 arquivos" in t or "arquivos listados" in t
    assert pastas.listar(str(arvore / "nao")).startswith("[ERRO]")
    raso = pastas.listar(str(arvore), profundidade=1)
    assert "src/ (2 itens)" in raso and "a.py" not in raso


def test_buscar(arvore):
    hits = pastas.buscar(str(arvore), "termo-x")
    assert {(h["arquivo"], h["linha"]) for h in hits} == {("src\\a.py", 2), ("src\\b.md", 2)}
    assert [h["arquivo"] for h in pastas.buscar(str(arvore), "termo-x", extensoes=".md")] == ["src\\b.md"]
    assert pastas.buscar(str(arvore), "") == []


@pytest.fixture
def raiz_git(tmp_path, monkeypatch):
    if not shutil.which("git"):
        pytest.skip("git ausente")
    raiz = tmp_path / "GitHub"
    repo = raiz / "proj"
    repo.mkdir(parents=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    import os
    env = {**os.environ, **env}
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True, env=env)
    (repo / "a.txt").write_text("1", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "inicio"], check=True, env=env)
    (repo / "b.txt").write_text("2", encoding="utf-8")
    (raiz / "nao_repo").mkdir()
    monkeypatch.setattr(pastas, "GIT_RAIZ", raiz)
    monkeypatch.setattr(execucao, "GIT_RAIZ", raiz)
    pastas._cache_repos.update(em=0.0, raiz=None, itens=[])
    return raiz, repo


def test_repos_listar(raiz_git):
    raiz, _ = raiz_git
    r = pastas.repos_listar(raiz)
    assert len(r) == 1 and r[0]["nome"] == "proj" and r[0]["ramo"] == "main" and r[0]["sujos"] == 1
    assert "inicio" in r[0]["ultimo_commit"]


def test_executar_git_e_deny_list(raiz_git, tmp_path):
    raiz, repo = raiz_git
    s = execucao.executar_git("proj", "status --porcelain")
    assert "[exit=0" in s and "?? b.txt" in s
    assert "[exit=0" in execucao.executar_git(str(repo), 'log -1 --format="%s"') and "inicio" in execucao.executar_git(str(repo), "log -1 --format=%s")
    for ruim in ("push --force", "push -f origin main", "reset --hard HEAD~1", "clean -fd", "branch -D main",
                 "checkout -- a.txt", "restore a.txt", "stash drop"):
        assert "deny-list" in execucao.executar_git("proj", ruim), ruim
    assert "--staged" in "restore --staged a.txt" and "deny-list" not in execucao.executar_git("proj", "restore --staged a.txt")
    assert execucao.executar_git(str(tmp_path), "status").startswith("[ERRO]")      # fora da raiz
    assert execucao.executar_git("nao_repo", "status").startswith("[ERRO]")         # nao e repo
    assert execucao.executar_git("proj", "").startswith("[ERRO]")


def test_rodar_script(tmp_path):
    s = tmp_path / "eco.py"
    s.write_text("import sys, os; print('args', sys.argv[1:], os.path.basename(os.getcwd()))", encoding="utf-8")
    r = execucao.rodar_script(s, 'um "dois tres" C:\\x', cwd=str(tmp_path))
    assert "[exit=0" in r and "['um', 'dois tres', 'C:/x']" in r and tmp_path.name in r
    assert execucao.rodar_script(tmp_path / "x.xyz").startswith("[ERRO]")
    assert "deny-list" in execucao.rodar_script(s, "rm -rf /")
    assert sys.executable.lower() == execucao.python_exe().lower()
