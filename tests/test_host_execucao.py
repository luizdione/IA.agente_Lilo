"""Ponte lilo-host, grupo exec: Python, R, WSL, deny-list e encerramento da arvore."""
from __future__ import annotations

import os
import shutil
import sys

import pytest

from lilo_host import execucao


@pytest.fixture(autouse=True)
def _trabalho(tmp_path, monkeypatch):
    monkeypatch.setattr(execucao, "TRABALHO", tmp_path / "trabalho")
    yield


def test_python_do_env():
    r = execucao.executar_python("import sys, os\nprint('ola', sys.version_info[:2], os.getcwd())")
    assert "[exit=0" in r and "ola (3, 11)" in r
    assert "trabalho" in r  # cwd padrao = pasta de trabalho da ponte
    assert not list(execucao.TRABALHO.glob("_lilo_*"))  # temporario removido


def test_python_erro_vai_para_stderr():
    r = execucao.executar_python("raise ValueError('boom')")
    assert "[exit=1" in r and "ValueError: boom" in r


def test_timeout_encerra_a_arvore():
    import psutil
    codigo = (
        "import subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "print('filho', p.pid, flush=True)\n"
        "time.sleep(120)\n"
    )
    r = execucao.executar_python(codigo, timeout=3)
    assert "[ERRO] tempo limite de 3 s" in r
    pid = int(r.split("filho ")[1].split()[0])
    assert not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE


def test_deny_list_bloqueia_sem_rodar():
    for fn, arg in ((execucao.executar_python, "import os; os.system('rm -rf / ')"),
                    (execucao.executar_wsl, "rm -rf ~"),
                    (execucao.executar_r, "system('shutdown now')")):
        r = fn(arg)
        assert r.startswith("[ERRO]") and "deny-list" in r


def test_saida_recortada():
    r = execucao.executar_python("print('x' * 20000)")
    assert "meio omitido" in r and len(r) < 10000


@pytest.mark.skipif(execucao.rscript_exe() is None, reason="Rscript ausente no env")
def test_r_do_env():
    r = execucao.executar_r("cat(1 + 1, '\\n'); cat(R.version$major)")
    assert "[exit=0" in r and "2" in r


@pytest.mark.skipif(os.name != "nt" or not shutil.which("wsl.exe"), reason="sem WSL")
def test_wsl():
    r = execucao.executar_wsl("echo ola-do-wsl && uname -s", timeout=60)
    if "executavel nao encontrado" in r or "[exit=-1" in r:
        pytest.skip("WSL instalado mas indisponivel: " + r[:120])
    assert "ola-do-wsl" in r and "Linux" in r


def test_rscript_ao_lado_do_python():
    rs = execucao.rscript_exe()
    if rs:
        assert rs.lower().startswith(os.path.dirname(sys.executable).lower())
