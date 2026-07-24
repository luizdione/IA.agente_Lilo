"""
shared/project_memory.py -- Leitor da memória .md dos projetos do dono
=====================================================================
Faz o LILO ler 100% da memória Markdown que o Claude + as skills
`/gerente_memoria_projeto` e `/salvar_contexto` geram em cada projeto.

Layout da memória (dois lugares, ambos lidos):
  <PROJETO>/.project-memory/PROJECT_STATE.md   (skill gerente_memoria_projeto)
  <PROJETO>/.project-memory/*.md               (DECISIONS/TASKS/CONTEXT/...)
  <PROJETO>/NEXT_SESSION.md                     (handoff da sessão)
  <PROJETO>/MEMORY.md, NOTES.md, ...            (skill salvar_contexto)

Uso:
    from shared.project_memory import list_projects, read_project, scan_all, digest_for
    projs = list_projects()                 # ['genomas', 'epigenoma', ...]
    mem = read_project("genomas")           # ProjectMemory(files={...})
    print(mem.digest())                     # resumo compacto (state + next)

Sem dependências pesadas (só stdlib). Não indexa nem embeda aqui -- isso é opção
da camada de RAG (scholar_brain); este módulo é a leitura crua/estruturada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Raiz dos projetos do dono (override por env em outra máquina).
DEFAULT_ROOT = r"C:\Users\luizd\OneDrive\Data_Science\Projetos"


def projects_root() -> Path:
    return Path(os.getenv("LILO_PROJECTS_ROOT", DEFAULT_ROOT))


# Arquivos de memória na RAIZ do projeto (skill salvar_contexto / convenções).
_ROOT_MEMORY_FILES = (
    "NEXT_SESSION.md", "MEMORY.md", "CONTEXT.md", "DECISIONS.md",
    "TASKS.md", "TODO.md", "NOTES.md", "CHANGELOG.md", "ARCHITECTURE.md",
    "CLAUDE.md",
)
_MEMORY_SUBDIR = ".project-memory"

# Ordem de prioridade para o digest compacto (o que mais importa primeiro).
# Alinhado ao layout REAL do PMM (skill gerente_memoria_projeto): o "onde parei"
# vive em PROJECT_STATE.md/CONTEXT.md (não há NEXT_SESSION.md dentro de
# .project-memory/); conhecimento durável em KNOWLEDGE.md. NEXT_SESSION.md/MEMORY.md
# continuam na lista porque ALGUNS projetos os têm na raiz (skill salvar_contexto).
_DIGEST_PRIORITY = ("PROJECT_STATE.md", "NEXT_SESSION.md", "CONTEXT.md",
                    "TASKS.md", "KNOWLEDGE.md", "MEMORY.md")


@dataclass
class ProjectMemory:
    """Memória .md de um projeto: nome, caminho e {arquivo -> texto}."""
    name: str
    path: str
    files: dict = field(default_factory=dict)   # nome_do_arquivo -> conteúdo

    @property
    def has_memory(self) -> bool:
        return bool(self.files)

    def get(self, filename: str, default: str = "") -> str:
        return self.files.get(filename, default)

    def full_text(self, max_chars: int = 0) -> str:
        """Concatena TODA a memória (prioritários primeiro), sem truncar por
        padrão (max_chars=0). É o backend de leitura 100% (tool lilo_project_memory)."""
        if not self.files:
            return "(sem memória .md para o projeto '%s')" % self.name
        order = [f for f in _DIGEST_PRIORITY if f in self.files]
        order += [f for f in sorted(self.files) if f not in order]
        text = "\n\n".join("### %s\n%s" % (f, self.files[f].strip()) for f in order)
        if max_chars and len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncado em %d chars]" % max_chars
        return text

    def digest(self, max_chars: int = 4000) -> str:
        """Resumo compacto: os arquivos prioritários (state/next/tasks),
        truncados, para injeção barata no contexto do route()."""
        if not self.files:
            return "(sem memória .md para o projeto '%s')" % self.name
        parts: list[str] = []
        seen: set[str] = set()
        budget = max_chars
        # 1) prioritários, na ordem definida
        for fname in _DIGEST_PRIORITY:
            if fname in self.files and budget > 0:
                seen.add(fname)
                chunk = self.files[fname].strip()
                if len(chunk) > budget:
                    chunk = chunk[:budget] + "\n...[truncado]"
                parts.append("### %s\n%s" % (fname, chunk))
                budget -= len(chunk)
        # 2) o resto (só títulos, para não estourar o budget)
        extras = [f for f in sorted(self.files) if f not in seen]
        if extras:
            parts.append("### (outros arquivos de memória) " + ", ".join(extras))
        return "\n\n".join(parts)


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def read_project(name: str, root: Path | None = None) -> ProjectMemory:
    """Lê TODA a memória .md de um projeto (subdir .project-memory/ + arquivos
    de memória na raiz). `name` pode conter subpasta (ex.: 'artigos_submissao/nss_virus')."""
    base = (root or projects_root()) / name
    files: dict[str, str] = {}

    subdir = base / _MEMORY_SUBDIR
    if subdir.is_dir():
        for md in sorted(subdir.glob("*.md")):
            files[md.name] = _read_text(md)

    for fname in _ROOT_MEMORY_FILES:
        fp = base / fname
        if fp.is_file():
            # nome da raiz não colide com os de .project-memory (nomes distintos);
            # se colidir, mantém o de .project-memory (não sobrescreve).
            files.setdefault(fname, _read_text(fp))

    return ProjectMemory(name=name, path=str(base), files=files)


def _has_any_memory(base: Path) -> bool:
    if (base / _MEMORY_SUBDIR).is_dir():
        return True
    return any((base / f).is_file() for f in _ROOT_MEMORY_FILES)


def list_projects(root: Path | None = None) -> list[str]:
    """Lista os projetos (subpastas da raiz) que TÊM memória .md."""
    r = root or projects_root()
    if not r.is_dir():
        return []
    out: list[str] = []
    for child in sorted(r.iterdir()):
        if child.is_dir() and _has_any_memory(child):
            out.append(child.name)
    return out


def scan_all(root: Path | None = None) -> dict[str, ProjectMemory]:
    """Indexa {projeto -> ProjectMemory} de todos os projetos com memória."""
    return {name: read_project(name, root=root) for name in list_projects(root)}


def digest_for(name: str, root: Path | None = None, max_chars: int = 4000) -> str:
    """Atalho: digest compacto da memória de um projeto (para o route())."""
    return read_project(name, root=root).digest(max_chars=max_chars)


def find_project_for_path(path: str | os.PathLike, root: Path | None = None) -> str | None:
    """Dado um caminho de trabalho, descobre a qual projeto ele pertence
    (para auto-injeção da memória no route() quando o LILO opera num projeto)."""
    r = (root or projects_root()).resolve()
    try:
        p = Path(path).resolve()
    except Exception:
        return None
    try:
        rel = p.relative_to(r)
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def read_full(name: str, root: Path | None = None, max_chars: int = 0) -> str:
    """Leitura 100% da memória de um projeto (backend da tool lilo_project_memory)."""
    return read_project(name, root=root).full_text(max_chars=max_chars)


def _resolve_project(hint, root: Path | None = None) -> "ProjectMemory | None":
    """Resolve `hint` -> ProjectMemory. `hint` pode ser um slug (sob projects_root)
    OU um caminho de diretório de projeto (ex.: o ctx['project_dir'] do dashboard)."""
    if hint is None:
        return None
    p = Path(str(hint))
    if p.is_dir():
        return read_project(p.name, root=p.parent)
    return read_project(str(hint), root=root)


def build_memory_context(hint, root: Path | None = None, max_chars: int = 4000) -> str:
    """Digest compacto da memória de um projeto para injeção no route().
    Aceita slug (sob projects_root) ou caminho absoluto. Vazio se sem memória."""
    mem = _resolve_project(hint, root)
    if not mem or not mem.has_memory:
        return ""
    return mem.digest(max_chars=max_chars)


def index(root: Path | None = None) -> list[dict]:
    """Índice leve {slug, path, files, updated_at} de todos os projetos com
    memória (backend da tool lilo_list_projects). Não carrega o conteúdo."""
    r = root or projects_root()
    out: list[dict] = []
    for name in list_projects(r):
        mem = read_project(name, root=r)
        # updated_at = mtime mais recente dos arquivos de memória
        mtimes = []
        subdir = (r / name) / _MEMORY_SUBDIR
        for md in list(subdir.glob("*.md")) if subdir.is_dir() else []:
            try:
                mtimes.append(md.stat().st_mtime)
            except Exception:
                pass
        out.append({
            "project": name,
            "path": mem.path,
            "files": sorted(mem.files.keys()),
            "n_files": len(mem.files),
            "updated_at": max(mtimes) if mtimes else 0.0,
        })
    return out


def search_memory(query: str, project: str | None = None, root: Path | None = None,
                  limit: int = 20, context_chars: int = 200) -> list[dict]:
    """Busca textual (substring case-insensitive; LIKE local, sem embeddings)
    na memória .md -- de um projeto ou de todos. Backend da tool
    lilo_project_memory_search. A indexação semântica (Chroma) é upgrade futuro."""
    q = (query or "").strip().lower()
    if not q:
        return []
    if project:
        projs = {project: read_project(project, root=root)}
    else:
        projs = scan_all(root=root)
    hits: list[dict] = []
    half = max(20, context_chars // 2)
    for slug, mem in projs.items():
        for fname, text in mem.files.items():
            low = text.lower()
            start = 0
            while True:
                i = low.find(q, start)
                if i < 0:
                    break
                a, b = max(0, i - half), i + len(q) + half
                snippet = " ".join(text[a:b].split())
                hits.append({"project": slug, "file": fname, "snippet": snippet})
                start = i + len(q)
                if len(hits) >= limit:
                    return hits
    return hits
