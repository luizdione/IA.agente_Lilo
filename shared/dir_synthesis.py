"""
shared/dir_synthesis.py -- Sintese offline de diretorios para LILO
==================================================================
Gera um arquivo .md descrevendo um diretorio: estrutura, arquivos-chave,
etapas concluidas e pendentes (heuristicas, sem LLM/tokens), estatisticas.

O .md gerado pode ser:
- aberto em nova aba do navegador (webbrowser.open)
- consultado por LILO para conhecer estado do projeto
- anexado as notas de um projeto (chat_memory.append_to_section)

Uso:
    from shared.dir_synthesis import synthesize_directory
    md_path = synthesize_directory(r"D:\\meu_projeto")
    # retorna Path absoluto para o .md gerado em data/syntheses/<hash>.md
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

# -- Config ------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]
SYNTH_DIR = _ROOT / "data" / "syntheses"

# Pastas que nao queremos descer (lixo, deps, builds)
_SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", "site-packages", ".next", ".turbo",
    "target", "out", ".cache", "coverage", ".coverage",
}

# Extensoes interessantes para contagem
_INTERESTING_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".sh", ".bat",
    ".md", ".rst", ".txt", ".yml", ".yaml", ".json", ".toml", ".ini",
    ".csv", ".tsv", ".xlsx", ".sql", ".db", ".sqlite",
    ".pdf", ".docx", ".pptx",
    ".ipynb", ".r", ".R", ".jl",
}

# Arquivos chave que detectamos e mostramos snippet
_KEY_FILES = [
    "README", "README.md", "README.rst", "README.txt",
    "CHANGELOG", "CHANGELOG.md",
    "TODO", "TODO.md", "PLAN.md", "ROADMAP.md",
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "Cargo.toml", "go.mod", "Gemfile",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "config.yaml", "config.yml", "config.toml",
    "LICENSE", "LICENSE.md", "LICENSE.txt",
]

# Limites para nao gerar .md gigante
_MAX_TREE_ENTRIES = 300
_MAX_FILE_SNIPPET_CHARS = 2000
_MAX_TODO_LINES = 50
_MAX_TREE_DEPTH = 4


# -- Helpers internos --------------------------------------------------------

def _safe_iter(path: Path) -> Iterable[Path]:
    try:
        return sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except (PermissionError, OSError):
        return []


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n = n / 1024
    return f"{n:.1f}PB"


def _build_tree(root: Path, max_depth: int = _MAX_TREE_DEPTH) -> tuple[list[str], int]:
    """Retorna (linhas da arvore ASCII, contagem de entradas)."""
    lines: list[str] = []
    count = 0

    def walk(p: Path, depth: int, prefix: str):
        nonlocal count
        if depth > max_depth or count >= _MAX_TREE_ENTRIES:
            return
        children = [c for c in _safe_iter(p) if c.name not in _SKIP_DIRS]
        for i, child in enumerate(children):
            if count >= _MAX_TREE_ENTRIES:
                lines.append(prefix + "... (truncado)")
                return
            is_last = i == len(children) - 1
            connector = "+-- " if is_last else "+-- "
            line = prefix + connector + child.name
            if child.is_dir():
                line += "/"
            else:
                try:
                    sz = child.stat().st_size
                    line += f"  ({_human_size(sz)})"
                except OSError:
                    pass
            lines.append(line)
            count += 1
            if child.is_dir():
                next_prefix = prefix + ("    " if is_last else "|   ")
                walk(child, depth + 1, next_prefix)

    walk(root, 0, "")
    return lines, count


def _read_text_safe(path: Path, limit: int = _MAX_FILE_SNIPPET_CHARS) -> str:
    """Le texto truncando, ignorando erros de encoding."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit + 1)
    except (OSError, UnicodeDecodeError):
        return ""


def _find_key_files(root: Path) -> list[Path]:
    """Encontra arquivos-chave no nivel raiz e ate 2 niveis abaixo."""
    found: list[Path] = []
    seen: set[str] = set()
    for p in root.rglob("*"):
        # limitar profundidade de busca
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if len(rel.parts) > 3:
            continue
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        if p.name in _KEY_FILES and p.is_file():
            key = p.name.lower()
            if key not in seen or "readme" in key:
                found.append(p)
                seen.add(key)
        if len(found) >= 20:
            break
    return found


def _collect_todos(root: Path) -> list[tuple[str, str]]:
    """Procura TODO/FIXME/XXX em arquivos de codigo. Retorna [(file, linha), ...]."""
    pattern = re.compile(r"(TODO|FIXME|XXX|HACK)[:\s].{0,120}", re.IGNORECASE)
    out: list[tuple[str, str]] = []
    code_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
                 ".java", ".c", ".cpp", ".rb", ".sh"}
    for p in root.rglob("*"):
        if len(out) >= _MAX_TODO_LINES:
            break
        if not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in code_exts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                rel = p.relative_to(root) if p.is_absolute() else p
                snippet = m.group(0).strip()
                out.append((f"{rel}:{line_no}", snippet))
                if len(out) >= _MAX_TODO_LINES:
                    break
    return out


def _git_log_summary(root: Path, n: int = 15) -> list[str]:
    """Se o diretorio for um repo git, retorna ultimos N commits."""
    if not (root / ".git").exists():
        return []
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={n}", "--pretty=format:%h %ad %s",
             "--date=short"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode == 0:
            return [ln for ln in result.stdout.splitlines() if ln.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return []


def _ext_stats(root: Path) -> tuple[dict[str, int], int, int]:
    """Conta arquivos por extensao + total de bytes + total de arquivos."""
    counts: dict[str, int] = {}
    total_bytes = 0
    total_files = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        ext = p.suffix.lower() or "(sem ext)"
        counts[ext] = counts.get(ext, 0) + 1
        try:
            total_bytes += p.stat().st_size
        except OSError:
            pass
        total_files += 1
    return counts, total_bytes, total_files


# -- Funcao principal --------------------------------------------------------

def synthesize_directory(path: str | Path,
                          out_dir: Path | None = None,
                          include_tree: bool = True,
                          include_todos: bool = True,
                          include_git: bool = True) -> Path:
    """
    Gera um arquivo .md sintetizando o diretorio.

    Args:
        path: caminho do diretorio (absoluto preferivel)
        out_dir: pasta onde salvar o .md (default: data/syntheses/)
        include_tree: incluir arvore de arquivos
        include_todos: buscar TODO/FIXME no codigo
        include_git: incluir git log (se for repo git)

    Returns:
        Path absoluto para o .md gerado.

    Raises:
        FileNotFoundError: se o diretorio nao existe
        NotADirectoryError: se o caminho nao for diretorio
    """
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Diretorio nao encontrado: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Nao e um diretorio: {root}")

    out_dir = Path(out_dir) if out_dir else SYNTH_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Hash do path para nome estavel (mesmo path = mesmo arquivo, sobrescreve)
    h = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:10]
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", root.name)[:40] or "dir"
    out_path = out_dir / f"{safe_name}_{h}.md"

    # Coletar dados
    counts, total_bytes, total_files = _ext_stats(root)
    key_files = _find_key_files(root)
    git_commits = _git_log_summary(root) if include_git else []
    todos = _collect_todos(root) if include_todos else []
    tree_lines, tree_count = (_build_tree(root) if include_tree else ([], 0))

    # Montar markdown
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"# Sintese de diretorio: {root.name}")
    lines.append("")
    lines.append(f"- **Caminho:** `{root}`")
    lines.append(f"- **Gerado em:** {now}")
    lines.append(f"- **Arquivos totais:** {total_files} ({_human_size(total_bytes)})")
    lines.append(f"- **Repositorio git:** {'sim' if (root / '.git').exists() else 'nao'}")
    lines.append("")

    # ---- Estado atual (heuristica) ----
    lines.append("## Estado atual")
    if git_commits:
        last = git_commits[0]
        lines.append(f"- Ultimo commit: `{last}`")
    if (root / "README.md").exists() or (root / "README").exists():
        lines.append("- Possui README.")
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        lines.append("- Projeto Python (deps configuradas).")
    if (root / "package.json").exists():
        lines.append("- Projeto Node/JS.")
    if not git_commits and not key_files:
        lines.append("- _Sem indicadores claros (sem git, sem manifestos)._")
    lines.append("")

    # ---- Etapas concluidas (commits recentes + CHANGELOG) ----
    lines.append("## Etapas concluidas (heuristica)")
    if git_commits:
        lines.append("**Commits recentes:**")
        lines.append("")
        for c in git_commits:
            lines.append(f"- {c}")
        lines.append("")
    changelog = next((p for p in key_files if p.name.lower().startswith("changelog")), None)
    if changelog:
        snippet = _read_text_safe(changelog, 1500)
        lines.append(f"**CHANGELOG ({changelog.name}):**")
        lines.append("")
        lines.append("```")
        lines.append(snippet[:1500])
        lines.append("```")
        lines.append("")
    if not git_commits and not changelog:
        lines.append("- _Nada detectado (sem git nem CHANGELOG)._")
        lines.append("")

    # ---- Etapas pendentes (TODO/FIXME + TODO.md/PLAN.md) ----
    lines.append("## Etapas pendentes (heuristica)")
    todo_md = next((p for p in key_files if p.name.lower() in
                    ("todo.md", "plan.md", "roadmap.md")), None)
    if todo_md:
        snippet = _read_text_safe(todo_md, 2000)
        lines.append(f"**{todo_md.name}:**")
        lines.append("")
        lines.append("```markdown")
        lines.append(snippet[:2000])
        lines.append("```")
        lines.append("")
    if todos:
        lines.append("**TODO/FIXME no codigo:**")
        lines.append("")
        for loc, txt in todos:
            lines.append(f"- `{loc}` — {txt}")
        lines.append("")
    if not todo_md and not todos:
        lines.append("- _Nenhum TODO/FIXME ou arquivo de plano encontrado._")
        lines.append("")

    # ---- Arquivos-chave (snippet de READMEs e manifestos) ----
    if key_files:
        lines.append("## Arquivos-chave")
        for kf in key_files:
            lines.append(f"### `{kf.relative_to(root)}`")
            snippet = _read_text_safe(kf, _MAX_FILE_SNIPPET_CHARS)
            if snippet:
                ext = kf.suffix.lower()
                fence = "markdown" if ext in (".md", ".rst") else ""
                lines.append("")
                lines.append(f"```{fence}")
                lines.append(snippet[:_MAX_FILE_SNIPPET_CHARS])
                if len(snippet) > _MAX_FILE_SNIPPET_CHARS:
                    lines.append("... (truncado)")
                lines.append("```")
                lines.append("")

    # ---- Estatisticas por extensao ----
    if counts:
        lines.append("## Estatisticas")
        lines.append("")
        lines.append("| Extensao | Arquivos |")
        lines.append("|----------|----------|")
        for ext, n in sorted(counts.items(), key=lambda x: -x[1])[:25]:
            lines.append(f"| `{ext}` | {n} |")
        lines.append("")

    # ---- Estrutura ----
    if include_tree and tree_lines:
        lines.append("## Estrutura (top niveis)")
        lines.append("")
        lines.append("```")
        for ln in tree_lines:
            lines.append(ln)
        if tree_count >= _MAX_TREE_ENTRIES:
            lines.append(f"... (truncado em {_MAX_TREE_ENTRIES} entradas)")
        lines.append("```")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def synthesis_to_html(md_path: Path) -> Path:
    """Converte o .md em .html simples (sem deps) para abrir no navegador.
    Markdown -> HTML basico (cabecalhos, listas, code blocks, tabelas)."""
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    md = md_path.read_text(encoding="utf-8")

    # Renderizacao MD->HTML minima (suficiente para visualizacao)
    try:
        import markdown  # type: ignore
        body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        # Fallback ultra-basico se a lib nao estiver instalada
        body = "<pre>" + md.replace("<", "&lt;").replace(">", "&gt;") + "</pre>"

    html = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>{md_path.stem}</title>
<style>
body {{ font-family: -apple-system,Segoe UI,Roboto,sans-serif;
       max-width: 920px; margin: 24px auto; padding: 0 18px;
       color: #222; background: #fafafa; line-height: 1.55; }}
h1,h2,h3 {{ color: #005A2D; }}
code {{ background: #eee; padding: 1px 5px; border-radius: 3px; }}
pre  {{ background: #1e1e1e; color: #eee; padding: 12px;
        border-radius: 6px; overflow-x: auto; font-size: 13px; }}
pre code {{ background: transparent; color: inherit; padding: 0; }}
table {{ border-collapse: collapse; margin: 10px 0; }}
th,td {{ border: 1px solid #ccc; padding: 6px 10px; }}
th {{ background: #ECEFF1; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    out_path = md_path.with_suffix(".html")
    out_path.write_text(html, encoding="utf-8")
    return out_path
