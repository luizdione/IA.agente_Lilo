"""Memoria `.project-memory` dos projetos do dono (grupo conhecimento).

Varre varias raizes ate 3 niveis (sao ~50 pastas `.project-memory` espalhadas em
`OneDrive\\...\\Projetos` e `C:\\github`, inclusive aninhadas). So stdlib; adaptado de
`origin/arch-v11:shared/project_memory.py`, que so olhava os filhos imediatos de
uma raiz.

Raizes: env `LILO_PROJETOS_RAIZES` (separadas por `;`), senao as duas do dono.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

RAIZES_PADRAO = (r"C:\Users\luizd\OneDrive\Data_Science\Projetos", r"C:\github")
PROFUNDIDADE = 3
SUBDIR = ".project-memory"
# Arquivos de memoria na raiz do projeto (skill salvar_contexto e convencoes antigas).
ARQS_RAIZ = ("NEXT_SESSION.md", "MEMORY.md", "CONTEXT.md", "DECISIONS.md", "TASKS.md",
             "TODO.md", "NOTES.md", "CHANGELOG.md", "ARCHITECTURE.md", "CLAUDE.md")
# O "onde parei" primeiro; o resto em ordem alfabetica.
PRIORIDADE = ("PROJECT_STATE.md", "NEXT_SESSION.md", "CONTEXT.md", "TASKS.md",
              "KNOWLEDGE.md", "MEMORY.md")
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", "archive", "_ARCHIVE_v10"}
_CACHE_SEG = 60.0


def raizes() -> list[Path]:
    env = os.environ.get("LILO_PROJETOS_RAIZES", "")
    partes = [p.strip() for p in env.split(";") if p.strip()] if env else list(RAIZES_PADRAO)
    return [Path(p) for p in partes if Path(p).is_dir()]


@dataclass
class Projeto:
    nome: str          # caminho relativo a raiz, com "/", unico entre as raizes
    caminho: Path
    arquivos: dict = field(default_factory=dict)   # nome -> texto

    def texto(self, max_chars: int = 0) -> str:
        if not self.arquivos:
            return "(projeto '%s' sem memoria .md)" % self.nome
        ordem = [a for a in PRIORIDADE if a in self.arquivos]
        ordem += [a for a in sorted(self.arquivos) if a not in ordem]
        t = "\n\n".join("### %s\n%s" % (a, self.arquivos[a].strip()) for a in ordem)
        if max_chars and len(t) > max_chars:
            t = t[:max_chars] + "\n...[truncado em %d caracteres; peca por arquivo]" % max_chars
        return t


def _tem_memoria(d: Path) -> bool:
    return (d / SUBDIR).is_dir()


def _varrer(raiz: Path, profundidade: int) -> list[Path]:
    achados: list[Path] = []
    pilha = [(raiz, 0)]
    while pilha:
        d, nivel = pilha.pop()
        try:
            filhos = [f for f in d.iterdir() if f.is_dir()]
        except OSError:
            continue
        for f in filhos:
            if f.name.startswith(".") or f.name in IGNORAR:
                continue
            if _tem_memoria(f):
                achados.append(f)
            if nivel + 1 < profundidade:
                pilha.append((f, nivel + 1))
    return sorted(achados)


_cache: dict = {"em": 0.0, "mapa": {}}


def mapa(forcar: bool = False) -> dict[str, Path]:
    """{nome -> pasta do projeto} de todas as raizes (cache de 60 s)."""
    if not forcar and time.time() - _cache["em"] < _CACHE_SEG and _cache["mapa"]:
        return _cache["mapa"]
    m: dict[str, Path] = {}
    for r in raizes():
        for p in _varrer(r, PROFUNDIDADE):
            nome = p.relative_to(r).as_posix()
            if nome in m:                       # mesmo nome em duas raizes
                nome = "%s@%s" % (nome, r.name)
            m[nome] = p
    _cache.update(em=time.time(), mapa=m)
    return m


def _ler(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def ler_projeto(nome: str) -> Projeto | None:
    """Toda a memoria .md de um projeto (`.project-memory/*.md` + arquivos da raiz)."""
    m = mapa()
    base = m.get(nome)
    if base is None:
        # tolera caminho absoluto da pasta do projeto
        p = Path(nome)
        if p.is_dir() and _tem_memoria(p):
            base = p
        else:
            return None
    arquivos: dict[str, str] = {}
    for md in sorted((base / SUBDIR).glob("*.md")):
        arquivos[md.name] = _ler(md)
    for a in ARQS_RAIZ:
        if (base / a).is_file():
            arquivos.setdefault(a, _ler(base / a))
    return Projeto(nome=nome, caminho=base, arquivos=arquivos)


def listar() -> list[dict]:
    """Indice leve: nome, pasta, n de arquivos, ultima atualizacao (sem conteudo)."""
    out = []
    for nome, p in mapa().items():
        mds = list((p / SUBDIR).glob("*.md"))
        mt = max((x.stat().st_mtime for x in mds), default=0.0)
        out.append({"nome": nome, "pasta": str(p), "arquivos": len(mds),
                    "atualizado": time.strftime("%Y-%m-%d", time.localtime(mt)) if mt else ""})
    return sorted(out, key=lambda d: d["atualizado"], reverse=True)


def buscar(consulta: str, projeto: str | None = None, limite: int = 20,
           contexto: int = 200) -> list[dict]:
    """Busca textual (substring, sem distinguir maiusculas) na memoria de um ou de todos."""
    q = (consulta or "").strip().lower()
    if not q:
        return []
    nomes = [projeto] if projeto else list(mapa())
    meio = max(20, contexto // 2)
    hits: list[dict] = []
    for nome in nomes:
        pj = ler_projeto(nome)
        if not pj:
            continue
        for arq, texto in pj.arquivos.items():
            baixo = texto.lower()
            i = baixo.find(q)
            while i >= 0:
                a, b = max(0, i - meio), i + len(q) + meio
                hits.append({"projeto": nome, "arquivo": arq,
                             "trecho": " ".join(texto[a:b].split())})
                if len(hits) >= limite:
                    return hits
                i = baixo.find(q, i + len(q))
    return hits
