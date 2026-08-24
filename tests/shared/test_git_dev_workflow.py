"""tests/shared/test_git_dev_workflow.py — V18.7 E7: git tools + dev_workflow.

Offline: repo git temporario de verdade (git init num tmp_path) para as git
tools; dev_workflow com runner de teste INJETADO (nao roda pytest recursivo)
e exec_mode em 'auto'. Cobre gate git_write, aborto em teste vermelho e o
guard do opt-in.
"""
from __future__ import annotations

import subprocess

import pytest

from shared import exec_mode, git_tools


def _init_repo(tmp_path):
    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True,
                       capture_output=True)
    g("init", "-q")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    g("commit", "--allow-empty", "-m", "raiz", "-q")
    return tmp_path


@pytest.fixture()
def repo(tmp_path):
    return _init_repo(tmp_path)


@pytest.fixture(autouse=True)
def _auto_mode():
    antes = exec_mode.get_mode()
    exec_mode.set_mode("auto")
    exec_mode._GRANT = False
    exec_mode._SCOPED_GRANTS.clear()
    yield
    exec_mode.set_mode(antes)


def test_git_status_e_diff_readonly(repo):
    (repo / "novo.txt").write_text("a", encoding="utf-8")
    st = git_tools.git_status(cwd=repo)
    assert "novo.txt" in st
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                   capture_output=True)
    diff = git_tools.git_diff(staged=True, cwd=repo)
    assert "novo.txt" in diff


def test_git_commit_em_auto_commita(repo):
    (repo / "f.txt").write_text("conteudo", encoding="utf-8")
    out = git_tools.git_commit("feat: teste", cwd=repo)
    assert "commit" in out and "criado" in out
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo,
                         capture_output=True, text=True).stdout
    assert "feat: teste" in log


def test_git_commit_em_plan_defere(repo):
    exec_mode.set_mode("plan")
    exec_mode.clear_plan()
    (repo / "f.txt").write_text("x", encoding="utf-8")
    out = git_tools.git_commit("feat: nao deveria commitar", cwd=repo)
    assert exec_mode.is_block(out)
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo,
                         capture_output=True, text=True).stdout
    assert "nao deveria" not in log  # nada commitado no modo plan


def test_git_commit_sem_mensagem(repo):
    assert "obrigatoria" in git_tools.git_commit("", cwd=repo)


def test_dev_workflow_desligado_por_padrao(monkeypatch):
    monkeypatch.delenv("LILO_DEV_WORKFLOW", raising=False)
    from shared.dev_workflow import run_dev_workflow
    out = run_dev_workflow("feat: x")
    assert "desligado" in out and "LILO_DEV_WORKFLOW" in out


def test_dev_workflow_aborta_em_teste_vermelho(monkeypatch):
    monkeypatch.setenv("LILO_DEV_WORKFLOW", "1")
    from shared.dev_workflow import run_dev_workflow
    out = run_dev_workflow("feat: x", runner=lambda t: (False, "1 failed"))
    assert "ABORTADO" in out and "vermelhos" in out


def test_dev_workflow_verde_encadeia(monkeypatch, repo):
    monkeypatch.setenv("LILO_DEV_WORKFLOW", "1")
    # aponta o PROJECT_ROOT das git tools para o repo temporario
    monkeypatch.setattr(git_tools, "PROJECT_ROOT", repo)
    (repo / "mud.txt").write_text("mudanca", encoding="utf-8")
    from shared.dev_workflow import run_dev_workflow
    out = run_dev_workflow("feat: verde", runner=lambda t: (True, "3 passed"))
    assert "1. testes" in out and "3 passed" in out
    assert "2. commit" in out and "criado" in out
    assert "OK: fluxo dev concluido" in out
