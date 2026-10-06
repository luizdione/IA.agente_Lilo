"""Pastas e repositorios do host, so leitura (grupo conhecimento).

"Anexar uma pasta" no LILO = citar o caminho na mensagem: o modelo lista com `listar`,
procura com `buscar` e le com ler_texto. `repos_listar` da o panorama de C:\\GitHub
(ramo, sujeira, ultimo commit) para o grupo exec agir com executar_git.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .comum import erro, resolver

GIT_RAIZ = Path(os.environ.get("LILO_GIT_RAIZ", r"C:\GitHub"))
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
TEXTO_EXT = {".py", ".r", ".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".ini",
             ".cfg", ".ps1", ".bat", ".sh", ".sql", ".html", ".css", ".js", ".ts", ".tex", ".bib",
             ".log", ".fasta", ".fa", ".gff", ".bed", ".vcf", ".sam", ".env.example", ".rst"}
BUSCA_MAX_BYTES = 2_000_000
_cache_repos: dict = {"em": 0.0, "raiz": None, "itens": []}


def _tamanho(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return "%d %s" % (n, unidade) if unidade == "B" else "%.1f %s" % (n, unidade)
        n /= 1024
    return str(n)


def listar(caminho: str, profundidade: int = 2, limite: int = 300) -> str:
    """Arvore da pasta (ate `profundidade` niveis, `limite` entradas) com tamanhos."""
    p = resolver(caminho)
    if not p.is_dir():
        return erro("pasta nao existe: %s" % p)
    profundidade = max(1, min(6, int(profundidade or 2)))
    linhas = [str(p)]
    n_arq = n_dir = 0
    total = 0
    cortado = False

    def anda(d: Path, nivel: int):
        nonlocal n_arq, n_dir, total, cortado
        try:
            filhos = sorted(d.iterdir(), key=lambda f: (f.is_file(), f.name.lower()))
        except OSError as e:
            linhas.append("  " * nivel + "[sem acesso: %s]" % e)
            return
        for f in filhos:
            if len(linhas) >= limite:
                cortado = True
                return
            if f.name in IGNORAR:
                continue
            if f.is_dir():
                n_dir += 1
                sub = sum(1 for _ in f.iterdir()) if nivel + 1 >= profundidade else None
                linhas.append("  " * nivel + f.name + "/" + (" (%d itens)" % sub if sub is not None else ""))
                if nivel + 1 < profundidade:
                    anda(f, nivel + 1)
            else:
                n_arq += 1
                try:
                    t = f.stat().st_size
                except OSError:
                    t = 0
                total += t
                linhas.append("  " * nivel + "%s  (%s)" % (f.name, _tamanho(t)))

    anda(p, 1)
    cabeca = "%d pastas, %d arquivos listados, %s%s" % (n_dir, n_arq, _tamanho(total),
                                                       "; lista cortada em %d entradas" % limite if cortado else "")
    return linhas[0] + "\n" + cabeca + "\n" + "\n".join(linhas[1:])


def buscar(caminho: str, termo: str, extensoes: str = "", limite: int = 50) -> list[dict] | str:
    """Procura `termo` (sem distinguir maiusculas) nos arquivos de texto da pasta; devolve
    arquivo, linha e trecho. `extensoes`: ".py,.md" para restringir."""
    p = resolver(caminho)
    if not p.is_dir():
        return erro("pasta nao existe: %s" % p)
    q = (termo or "").strip()
    if not q:
        return []
    exts = {e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower()
            for e in extensoes.split(",") if e.strip()} or TEXTO_EXT
    rx = re.compile(re.escape(q), re.IGNORECASE)
    hits: list[dict] = []
    for raiz, dirs, arquivos in os.walk(p):
        dirs[:] = [d for d in dirs if d not in IGNORAR and not d.startswith(".")]
        for nome in arquivos:
            f = Path(raiz) / nome
            if f.suffix.lower() not in exts:
                continue
            try:
                if f.stat().st_size > BUSCA_MAX_BYTES:
                    continue
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    for n, linha in enumerate(fh, 1):
                        if rx.search(linha):
                            hits.append({"arquivo": str(f.relative_to(p)), "linha": n,
                                         "trecho": linha.strip()[:200]})
                            if len(hits) >= limite:
                                return hits
            except OSError:
                continue
    return hits


def _git(repo: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def repos_listar(raiz: Path | None = None) -> list[dict]:
    """Repositorios git em C:\\GitHub: nome, ramo, arquivos sujos, ultimo commit (cache 60 s)."""
    raiz = raiz or GIT_RAIZ
    if (_cache_repos["raiz"] == str(raiz) and time.time() - _cache_repos["em"] < 60):
        return _cache_repos["itens"]
    out = []
    if raiz.is_dir():
        for d in sorted(raiz.iterdir()):
            if not (d / ".git").exists():
                continue
            status = _git(d, "status", "--porcelain", "--branch")
            linhas = status.splitlines()
            ramo = linhas[0][3:].split("...")[0] if linhas else "?"
            sujos = max(0, len(linhas) - 1)
            ultimo = _git(d, "log", "-1", "--format=%cs %s")
            out.append({"nome": d.name, "ramo": ramo, "sujos": sujos, "ultimo_commit": ultimo[:90],
                        "caminho": str(d)})
    _cache_repos.update(em=time.time(), raiz=str(raiz), itens=out)
    return out
