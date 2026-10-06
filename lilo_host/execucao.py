"""Execucao no host (grupo exec): Python do env datascience, Rscript do mesmo env e WSL.

Regras: deny-list de comandos (comum.PADROES_PROIBIDOS) aplicada ao codigo e ao
comando; tempo limite com encerramento da ARVORE de processos (psutil; taskkill
como reserva); pasta de trabalho propria (comum.TRABALHO) como cwd padrao; saida
recortada (8000 stdout / 2000 stderr). Sem `conda run`: o Python e o
`sys.executable` deste processo (o servidor ja roda no env) e o R e o
`Scripts\\Rscript.exe` ao lado dele.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .comum import TRABALHO, comando_proibido, erro, recortar

STDOUT_MAX = 8000
STDERR_MAX = 2000
TIMEOUT_MAX = 900
WSL_DISTRO = os.environ.get("LILO_WSL_DISTRO", "Ubuntu")


def python_exe() -> str:
    return sys.executable


def rscript_exe() -> str | None:
    base = Path(sys.executable).parent
    for c in (base / "Scripts" / "Rscript.exe", base / "Lib" / "R" / "bin" / "Rscript.exe",
              base / "bin" / "Rscript"):
        if c.exists():
            return str(c)
    return None


def ambiente() -> dict[str, str]:
    """Ambiente dos filhos: PATH com o env na frente (DLLs do R/numpy), UTF-8 na saida."""
    env = dict(os.environ)
    base = Path(sys.executable).parent
    frente = [str(base), str(base / "Scripts"), str(base / "Library" / "bin"), str(base / "Library" / "mingw-w64" / "bin")]
    atual = [p for p in env.get("PATH", "").split(os.pathsep) if p and p not in frente]
    env["PATH"] = os.pathsep.join(frente + atual)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _matar_arvore(pid: int) -> None:
    try:
        import psutil
        pai = psutil.Process(pid)
        filhos = pai.children(recursive=True)
        for p in filhos + [pai]:
            try:
                p.kill()
            except psutil.Error:
                pass
        psutil.wait_procs(filhos + [pai], timeout=5)
    except Exception:  # noqa: BLE001 — reserva: taskkill / killpg
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            import signal
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except OSError:
                pass


def _fmt(codigo: int | None, out: str, err: str, segundos: float) -> str:
    partes = ["[exit=%s em %.1f s]" % (codigo, segundos)]
    partes.append("--- STDOUT ---\n" + recortar(out or "", STDOUT_MAX))
    if err:
        partes.append("--- STDERR ---\n" + recortar(err, STDERR_MAX))
    return "\n".join(partes)


def rodar(argv: list[str], timeout: int = 120, cwd: str | None = None) -> str:
    """Roda argv com tempo limite; no estouro encerra a arvore inteira."""
    timeout = max(1, min(TIMEOUT_MAX, int(timeout or 120)))
    pasta = Path(cwd) if cwd else TRABALHO
    pasta.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, cwd=str(pasta), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                errors="replace", env=ambiente(), creationflags=flags,
                                start_new_session=(os.name != "nt"))
    except FileNotFoundError as e:
        return erro("executavel nao encontrado: %s" % e)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _matar_arvore(proc.pid)
        out, err = proc.communicate()
        return (erro("tempo limite de %d s estourado; arvore de processos encerrada" % timeout)
                + "\n" + _fmt(proc.returncode, out, err, time.perf_counter() - t0))
    return _fmt(proc.returncode, out, err, time.perf_counter() - t0)


def _temporario(sufixo: str, conteudo: str, cwd: str | None) -> Path:
    pasta = Path(cwd) if cwd else TRABALHO
    pasta.mkdir(parents=True, exist_ok=True)
    p = pasta / ("_lilo_%d_%d%s" % (os.getpid(), int(time.time() * 1000), sufixo))
    p.write_text(conteudo, encoding="utf-8")
    return p


def executar_python(codigo: str, timeout: int = 120, cwd: str | None = None) -> str:
    """Roda codigo Python no env datascience (pandas, scipy, Biopython...)."""
    pad = comando_proibido(codigo)
    if pad:
        return erro("codigo bloqueado pela deny-list (%s)" % pad)
    arq = _temporario(".py", codigo, cwd)
    try:
        return rodar([python_exe(), "-X", "utf8", str(arq)], timeout, cwd)
    finally:
        arq.unlink(missing_ok=True)


def executar_r(codigo: str, timeout: int = 180, cwd: str | None = None) -> str:
    """Roda codigo R (Rscript 4.5 do env datascience)."""
    pad = comando_proibido(codigo)
    if pad:
        return erro("codigo bloqueado pela deny-list (%s)" % pad)
    rs = rscript_exe()
    if not rs:
        return erro("Rscript nao encontrado ao lado de %s" % sys.executable)
    arq = _temporario(".R", codigo, cwd)
    try:
        return rodar([rs, "--vanilla", str(arq)], timeout, cwd)
    finally:
        arq.unlink(missing_ok=True)


def executar_wsl(comando: str, timeout: int = 120, distro: str | None = None) -> str:
    """Roda um comando bash no WSL (distro Ubuntu por padrao)."""
    pad = comando_proibido(comando)
    if pad:
        return erro("comando bloqueado pela deny-list (%s)" % pad)
    return rodar(["wsl.exe", "-d", distro or WSL_DISTRO, "--", "bash", "-lc", comando], timeout)
