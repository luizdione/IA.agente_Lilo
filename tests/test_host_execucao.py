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
    # A ponte roda o Python do proprio processo (sys.executable): 3.11 no datascience, 3.12 no CI.
    assert "[exit=0" in r and f"ola {sys.version_info[:2]}" in r
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


_PS = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(not _PS, reason="sem PowerShell")
def test_powershell_basico_utf8_e_exit(tmp_path, monkeypatch):
    from lilo_host import comum
    monkeypatch.setattr(comum, "RAIZES", [tmp_path])
    r = execucao.executar_powershell("Write-Output 'ola ação'; (Get-Location).Path", cwd=str(tmp_path))
    assert "[exit=0" in r and "ola ação" in r and tmp_path.name in r
    assert "[exit=3" in execucao.executar_powershell("exit 3", cwd=str(tmp_path))
    r2 = execucao.executar_powershell('python -c "import sys; print(sys.executable)"', cwd=str(tmp_path))
    assert "[exit=0" in r2 and "python" in r2.lower()
    assert not list(tmp_path.glob("_lilo_*"))   # .ps1 temporario removido


@pytest.mark.skipif(not _PS, reason="sem PowerShell")
def test_powershell_deny_list_cwd_e_timeout(tmp_path, monkeypatch):
    from lilo_host import comum
    monkeypatch.setattr(comum, "RAIZES", [tmp_path])
    for cmd in ("Invoke-WebRequest https://x", "curl https://x", "iex 'x'", "Remove-Item -Recurse -Force C:\\",
                "powershell -enc AAAAAAAAAAAAAAAAAAAAAAAAAAAA", "git push --force", "shutdown /s",
                "reg delete HKCU\\x", "Set-MpPreference -DisableRealtimeMonitoring 1"):
        r = execucao.executar_powershell(cmd, cwd=str(tmp_path))
        assert r.startswith("[ERRO]") and "deny-list" in r, cmd
    assert "fora das raizes" in execucao.executar_powershell("Write-Output 1", cwd=str(tmp_path.parent))
    assert "vazio" in execucao.executar_powershell("  ")
    r = execucao.executar_powershell("Start-Sleep -Seconds 30", cwd=str(tmp_path), timeout=2)
    assert "[ERRO] tempo limite de 2 s" in r
    assert not list(tmp_path.glob("_lilo_*"))
