"""
shared/exec_env.py -- Ambientes de execução do LILO (conda envs + WSL)
=====================================================================
Dá ao LILO acesso ao ambiente real de análise do dono: os envs conda/miniforge
(Python + R) e o WSL (Ubuntu). Assim os subagentes -- depois de o roteador ML
decidir -- podem rodar QUALQUER pacote instalado, local, sem gastar token de nuvem.

Runners puros (SEM gating): a política de segurança (exec_mode plan/ask/auto +
bloqueio de comandos perigosos) é aplicada na CAMADA do agente `desktop`, que é
quem expõe estas capacidades como tools. Este módulo só localiza os ambientes e
executa em subprocess isolado.

Descoberta (override por env):
  LILO_CONDA_BASE   raiz do conda/miniforge (default: C:\\Users\\luizd\\miniforge3)
  LILO_PY_ENV       env conda de análise padrão (default: datascience)
  LILO_WSL_DISTRO   distro WSL padrão (default: Ubuntu)

Uso:
    from shared.exec_env import run_python, run_r, run_wsl, list_conda_envs, env_info
    print(run_python("import numpy as np; print(np.__version__)"))     # no datascience
    print(run_wsl("uname -a"))
"""
from __future__ import annotations

import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from .logger import get_logger

log = get_logger("ExecEnv")

DEFAULT_CONDA_BASE = r"C:\Users\luizd\miniforge3"
DEFAULT_PY_ENV = "datascience"
DEFAULT_WSL_DISTRO = "Ubuntu"

_OUT_CAP = 8000   # limite de STDOUT no retorno
_ERR_CAP = 4000   # limite de STDERR no retorno


# ── Localização do conda ─────────────────────────────────────────────────────

def conda_base() -> Path:
    return Path(os.getenv("LILO_CONDA_BASE", DEFAULT_CONDA_BASE))


def default_py_env() -> str:
    return os.getenv("LILO_PY_ENV", DEFAULT_PY_ENV)


def default_wsl_distro() -> str:
    return os.getenv("LILO_WSL_DISTRO", DEFAULT_WSL_DISTRO)


@lru_cache(maxsize=1)
def conda_exe() -> str | None:
    """Caminho do executável conda. PATH > <base>/Scripts/conda.exe (Win) >
    <base>/condabin/conda.bat > <base>/bin/conda (Unix). None se não achar."""
    from shutil import which
    onpath = which("conda")
    if onpath:
        return onpath
    base = conda_base()
    cands = [
        base / "Scripts" / "conda.exe",
        base / "condabin" / "conda.bat",
        base / "bin" / "conda",
    ]
    for c in cands:
        if c.exists():
            return str(c)
    return None


# ── Execução crua ────────────────────────────────────────────────────────────

def _fmt(rc: int, out: str, err: str) -> str:
    return (
        "[exit=%d]\n--- STDOUT ---\n%s\n--- STDERR ---\n%s"
        % (rc, (out or "")[:_OUT_CAP], (err or "")[:_ERR_CAP])
    )


def _run(argv: list[str], timeout: int, cwd: str | None = None) -> str:
    try:
        r = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout,
            cwd=cwd, encoding="utf-8", errors="replace",
        )
        return _fmt(r.returncode, r.stdout, r.stderr)
    except FileNotFoundError as e:
        return "[ERRO] executável não encontrado: %s" % e
    except subprocess.TimeoutExpired:
        return "[ERRO] timeout após %ds" % timeout
    except Exception as e:  # noqa: BLE001
        return "[ERRO] %s" % e


# ── Runners de alto nível ────────────────────────────────────────────────────

def list_conda_envs() -> list[str]:
    """Nomes dos envs conda (base, datascience, ...). [] se conda ausente."""
    exe = conda_exe()
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "env", "list"], capture_output=True, text=True,
                           timeout=30, encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        log.debug("conda env list falhou: %s", e)
        return []
    envs = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split()[0]
        if name and name != "*":
            envs.append(name)
    return envs


def run_python(code: str, env: str | None = None, timeout: int = 120,
               cwd: str | None = None) -> str:
    """Executa `code` Python. env=None -> Python do próprio LILO; caso contrário
    `conda run -n <env> python -c code` (default: env de análise 'datascience')."""
    env = default_py_env() if env is None else env
    if env in ("", "self", "lilo"):
        return _run([sys.executable, "-c", code], timeout, cwd)
    exe = conda_exe()
    if not exe:
        return ("[ERRO] conda não encontrado (LILO_CONDA_BASE=%s). "
                "Rodando no Python do LILO como fallback.\n" % conda_base()
                + _run([sys.executable, "-c", code], timeout, cwd))
    return _run([exe, "run", "-n", env, "python", "-c", code], timeout, cwd)


def run_script(script_path: str, args=None, env: str | None = None,
               timeout: int = 300, cwd: str | None = None) -> str:
    """Roda um SCRIPT Python (arquivo .py) com argumentos de linha de comando,
    no env conda de análise (default 'datascience', que tem os pacotes). É o
    motor das skills portadas (lilo_skills). `args` pode ser lista OU string
    (recomenda-se caminhos com / ou passar como lista para evitar problemas de
    escape no Windows)."""
    env = default_py_env() if env is None else env
    if args is None:
        argv_args = []
    elif isinstance(args, str):
        import shlex
        argv_args = shlex.split(args) if args.strip() else []
    else:
        argv_args = [str(a) for a in args]
    exe = conda_exe()
    if env in ("", "self", "lilo") or not exe:
        return _run([sys.executable, script_path, *argv_args], timeout, cwd)
    return _run([exe, "run", "-n", env, "python", script_path, *argv_args],
                timeout, cwd)


def run_r(code: str, env: str | None = None, timeout: int = 180,
          cwd: str | None = None) -> str:
    """Executa `code` R via `conda run -n <env> Rscript -e code`. Se o R não
    estiver instalado no env, retorna dica acionável (não silencioso)."""
    env = default_py_env() if env is None else env
    exe = conda_exe()
    if not exe:
        return "[ERRO] conda não encontrado (LILO_CONDA_BASE=%s)" % conda_base()
    out = _run([exe, "run", "-n", env, "Rscript", "-e", code], timeout, cwd)
    if ("não é reconhecido" in out or "not recognized" in out
            or "No such file" in out or "command not found" in out):
        out += ("\n[LILO] R/Rscript não encontrado no env '%s'. Instale com: "
                "conda install -n %s -c conda-forge r-base  (ou aponte LILO_PY_ENV "
                "para um env com R, ou instale R no WSL e use run_wsl)." % (env, env))
    return out


def run_wsl(cmd: str, distro: str | None = None, timeout: int = 120) -> str:
    """Executa `cmd` no WSL via `wsl.exe -d <distro> -- bash -lc cmd`."""
    distro = default_wsl_distro() if distro is None else distro
    return _run(["wsl.exe", "-d", distro, "--", "bash", "-lc", cmd], timeout)


def list_wsl_distros() -> list[str]:
    """Distros WSL instaladas. [] se WSL ausente."""
    try:
        r = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, text=True,
                           timeout=15, encoding="utf-16-le", errors="replace")
        names = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        # -l -q às vezes vem com \x00; limpa resíduos.
        return [n.replace("\x00", "") for n in names if n.replace("\x00", "")]
    except Exception:  # noqa: BLE001
        return []


def env_info() -> dict:
    """Resumo das capacidades de execução -- para o roteador/subagentes saberem
    o que está disponível (conda envs, WSL, Python padrão)."""
    exe = conda_exe()
    return {
        "conda_base": str(conda_base()),
        "conda_found": bool(exe),
        "conda_exe": exe or "",
        "conda_envs": list_conda_envs(),
        "default_py_env": default_py_env(),
        "wsl_distros": list_wsl_distros(),
        "default_wsl_distro": default_wsl_distro(),
        "lilo_python": sys.executable,
    }
