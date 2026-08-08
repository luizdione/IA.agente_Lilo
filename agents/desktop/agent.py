"""
agents/desktop/agent.py -- Desktop Commander para LILO
=======================================================
Tools de sistema operacional acessiveis ao Claude Desktop e PyCharm via MCP,
e tambem ao dashboard Streamlit 8100. Inspirado no @desktop_commander, mas
restrito a diretorios permitidos (allow-list) por seguranca.

Tools expostas:
  fs_read(path, max_bytes=200000)         -- le arquivo texto
  fs_write(path, content, append=False)   -- escreve/anexa em arquivo
  fs_list(path, glob="*", recursive=False) -- lista diretorio
  fs_stat(path)                           -- metadados (tamanho, mtime)
  fs_search(root, pattern, regex=False)   -- grep recursivo
  fs_move(src, dst)                       -- move/renomeia
  run_shell(cmd, cwd=None, timeout=60)    -- executa comando shell
  run_python(code, timeout=60)            -- executa snippet Python isolado

Seguranca:
- Le LILO_DESKTOP_ALLOW de .env (separado por ;) para definir diretorios permitidos.
- Default: raiz do LILO + workspace selecionado.
- Bloqueia paths fora da allow-list e comandos perigosos (rm -rf /, format c:, etc.).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent  # noqa: E402
from shared.utils import load_env, get_env  # noqa: E402

load_env()


# -- Allow-list de diretorios -----------------------------------------------

def _build_allowlist() -> list[Path]:
    """Constroi a lista de diretorios onde o agent pode ler/escrever.
    Le de LILO_DESKTOP_ALLOW (paths separados por ; no Windows ou : no Unix).
    Default: raiz do LILO."""
    raw = get_env("LILO_DESKTOP_ALLOW", "")
    sep = ";" if os.name == "nt" else ":"
    paths = [p.strip() for p in raw.split(sep) if p.strip()] if raw else []
    if not paths:
        paths = [str(_ROOT)]  # default: raiz do projeto LILO
    out = []
    for p in paths:
        try:
            r = Path(p).expanduser().resolve()
            if r.exists():
                out.append(r)
        except Exception:
            pass
    return out


ALLOWLIST = _build_allowlist()


# -- Validacoes --------------------------------------------------------------

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",          # rm -rf /
    r"\brm\s+-rf\s+~",          # rm -rf ~
    r"\bformat\s+[a-z]:",       # format c:
    r"\bdel\s+/[fsq]\s+",       # del /f /s /q ...
    r":\(\)\s*\{\s*:\|:&\s*\}",  # fork bomb
    r"\bmkfs\b",                 # mkfs
    r"\bdd\s+if=.+of=/dev/",    # dd to device
    r">\s*/dev/sd[a-z]",         # write to disk
    r"\bshutdown\b",
    r"\breboot\b",
]

# V15 FASE 1: escrita em git NAO e "perigosa" (nao bloqueia), mas e SENSIVEL ->
# never-commit-unless-asked. Passa por exec_mode.gate('git_write') com grant
# escopado, sensivel ate no modo 'auto'. Protege manuscritos (skill git_dione)
# de push acidental.
GIT_WRITE_PATTERNS = [
    r"\bgit\s+(commit|push)\b",
    r"\bgit\b.*\s--force\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-zA-Z]*f",
]


def _is_path_allowed(path: Path) -> tuple[bool, str]:
    """Retorna (ok, motivo)."""
    try:
        p = path.expanduser().resolve()
    except Exception as e:
        return False, f"path invalido: {e}"
    for allowed in ALLOWLIST:
        try:
            p.relative_to(allowed)
            return True, ""
        except ValueError:
            continue
    return False, (
        "path fora da allow-list. Permitidos: "
        + " ; ".join(str(a) for a in ALLOWLIST)
        + ". Edite LILO_DESKTOP_ALLOW no .env para incluir mais."
    )


def _is_cmd_dangerous(cmd: str) -> Optional[str]:
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return pat
    return None


def _is_git_write(cmd: str) -> Optional[str]:
    for pat in GIT_WRITE_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return pat
    return None


# -- Operacoes ---------------------------------------------------------------

def fs_read(path: str, max_bytes: int = 200_000) -> str:
    p = Path(path)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.exists():
        return f"[ERRO] arquivo nao existe: {path}"
    if not p.is_file():
        return f"[ERRO] nao e arquivo: {path}"
    try:
        data = p.read_bytes()[:max_bytes]
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")
    except Exception as e:
        return f"[ERRO] {e}"


def fs_write(path: str, content: str, append: bool = False) -> str:
    p = Path(path)
    ok, why = _is_path_allowed(p)
    if not ok:
        # V14: escrita FORA da allow-list -> ação de risco sujeita aos modos.
        from shared import exec_mode as _xm
        g = _xm.gate("write_outside", str(p))
        return g if g else f"[ERRO] {why}"
    # V14: gating por modo (plan bloqueia; ask confirma; accept_edits/auto passam).
    from shared import exec_mode as _xm
    _g = _xm.gate("write", "%s (%d chars)" % (p, len(content)))
    if _g:
        return _g
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        if append:
            # Append: O_APPEND ja e atomico por escrita; mantem semantica.
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            # Overwrite ATOMICO (tmp + fsync + os.replace): elimina a classe
            # de arquivo meio-escrito/truncado que corrompeu agent.py quando
            # uma gravacao foi interrompida (limite de creditos/crash).
            # Ver relatorios 2026-06-04/05/06 (pendencia P1). V10.8.
            tmp = p.with_suffix(p.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)
        return f"[OK] {'append' if append else 'write'} -> {p} ({len(content)} chars)"
    except Exception as e:
        # Limpa o tmp orfao em caso de falha no caminho atomico.
        try:
            if not append and 'tmp' in locals() and tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return f"[ERRO] {e}"


def fs_list(path: str, glob: str = "*", recursive: bool = False, limit: int = 200) -> str:
    p = Path(path)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.is_dir():
        return f"[ERRO] nao e diretorio: {path}"
    try:
        if recursive:
            items = list(p.rglob(glob))
        else:
            items = list(p.glob(glob))
        items = sorted(items)[:limit]
        lines = []
        for it in items:
            kind = "DIR " if it.is_dir() else "FILE"
            try:
                size = it.stat().st_size if it.is_file() else 0
            except OSError:
                size = 0
            rel = it.relative_to(p) if it.is_relative_to(p) else it
            lines.append(f"{kind}  {size:>12,d}  {rel}")
        return "\n".join(lines) if lines else "(vazio)"
    except Exception as e:
        return f"[ERRO] {e}"


def fs_stat(path: str) -> str:
    p = Path(path)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.exists():
        return f"[ERRO] nao existe: {path}"
    s = p.stat()
    return (
        f"path: {p}\n"
        f"type: {'directory' if p.is_dir() else 'file'}\n"
        f"size: {s.st_size:,} bytes\n"
        f"mtime: {datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
    )


def fs_search(root: str, pattern: str, regex: bool = False, limit: int = 50) -> str:
    p = Path(root)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.is_dir():
        return f"[ERRO] nao e diretorio: {root}"
    matcher = re.compile(pattern) if regex else None
    hits = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if matcher:
            for m in matcher.finditer(text):
                hits.append(f"{f}:{text[:m.start()].count(chr(10))+1}: {m.group(0)[:80]}")
                if len(hits) >= limit:
                    return "\n".join(hits)
        else:
            for i, line in enumerate(text.splitlines(), 1):
                if pattern in line:
                    hits.append(f"{f}:{i}: {line.strip()[:120]}")
                    if len(hits) >= limit:
                        return "\n".join(hits)
    return "\n".join(hits) if hits else "(sem matches)"


def fs_move(src: str, dst: str) -> str:
    sp, dp = Path(src), Path(dst)
    for p in (sp, dp):
        ok, why = _is_path_allowed(p)
        if not ok:
            return f"[ERRO] {why}"
    try:
        shutil.move(str(sp), str(dp))
        return f"[OK] {sp} -> {dp}"
    except Exception as e:
        return f"[ERRO] {e}"


def run_shell(cmd: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
    danger = _is_cmd_dangerous(cmd)
    if danger:
        return f"[ERRO] comando perigoso bloqueado (pattern: {danger})"
    # V14: shell e acao de RISCO -> sujeita aos modos (plan/ask confirmam/bloqueiam).
    # V15 FASE 1: git commit/push/reset/--force usam o gate 'git_write' (sensivel
    # ate em 'auto', grant escopado ao cmd) -> never-commit-unless-asked.
    from shared import exec_mode as _xm
    if _is_git_write(cmd):
        _gg = _xm.gate("git_write", cmd, token=_xm.scope_token(cmd))
        if _gg:
            return _gg
    else:
        _g = _xm.gate("shell", cmd)
        if _g:
            return _g
    if cwd:
        ok, why = _is_path_allowed(Path(cwd))
        if not ok:
            return f"[ERRO] cwd: {why}"
    try:
        # Windows: shell=True para suportar dir, cd, etc.
        # Unix: shell=True com /bin/sh
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        out = r.stdout or ""
        err = r.stderr or ""
        return (
            f"[exit={r.returncode}]\n"
            f"--- STDOUT ---\n{out[:8000]}\n"
            f"--- STDERR ---\n{err[:2000]}"
        )
    except subprocess.TimeoutExpired:
        return f"[ERRO] timeout apos {timeout}s"
    except Exception as e:
        return f"[ERRO] {e}"


def run_python(code: str, timeout: int = 60) -> str:
    """Executa snippet Python em subprocess isolado (nao no proc do MCP)."""
    # V14: execucao de codigo e RISCO -> sujeita aos modos.
    from shared import exec_mode as _xm
    _g = _xm.gate("python", code[:200])
    if _g:
        return _g
    if any(b in code for b in ["os.system", "subprocess.call", "subprocess.run"]):
        # snippets podem chamar shell, mas avisamos
        pass
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return (
            f"[exit={r.returncode}]\n"
            f"--- STDOUT ---\n{r.stdout[:8000]}\n"
            f"--- STDERR ---\n{r.stderr[:2000]}"
        )
    except subprocess.TimeoutExpired:
        return f"[ERRO] timeout apos {timeout}s"
    except Exception as e:
        return f"[ERRO] {e}"


# -- BaseAgent wrapper -------------------------------------------------------

class DesktopAgent(BaseAgent):
    """Subagente Desktop Commander.
    Expoe filesystem + shell com allow-list de diretorios."""

    name = "desktop"
    description = (
        "Desktop Commander LILO: ler/escrever arquivos, listar diretorios, "
        "executar shell e Python. Restrito a allow-list (LILO_DESKTOP_ALLOW)."
    )
    KEYWORDS = ["arquivo", "file", "diretorio", "directory", "ls", "cat",
                "shell", "bash", "cmd", "powershell", "executar",
                "listar", "criar arquivo", "ler arquivo"]

    # V9 (2026-05-22): roteamento cost-aware no Villa_Lobos.
    # Operações de filesystem/shell são locais e rápidas (sem LLM no caminho).
    cost_tier = "ollama"
    local_only = True
    latency_class = "fast"

    def run(self, query: str, context: dict[str, Any] = None) -> str:
        """Roteamento simples: o caller deve preferir as tools individuais.
        Se chamado via run() generico, faz best-effort."""
        ctx = context or {}
        op = ctx.get("op", "list")
        if op == "read":
            return fs_read(ctx.get("path", ""), ctx.get("max_bytes", 200_000))
        if op == "write":
            return fs_write(ctx.get("path", ""), ctx.get("content", ""),
                            ctx.get("append", False))
        if op == "list":
            return fs_list(ctx.get("path", str(_ROOT)),
                           ctx.get("glob", "*"),
                           ctx.get("recursive", False))
        if op == "shell":
            return run_shell(ctx.get("cmd", query), ctx.get("cwd"),
                             ctx.get("timeout", 60))
        if op == "python":
            return run_python(ctx.get("code", query), ctx.get("timeout", 60))
        if op == "search":
            return fs_search(ctx.get("root", str(_ROOT)),
                             ctx.get("pattern", query),
                             ctx.get("regex", False))
        return f"[DesktopAgent] op desconhecida: {op}"

    # V18.5 (bugfix): metodos-delegadores para as funcoes de modulo. O
    # Explorer do Villa no dashboard chama _desktop.fs_list/fs_read/fs_write
    # como METODOS (AttributeError: 'DesktopAgent' object has no attribute
    # 'fs_list'); expor delegadores conserta sem duplicar logica e mantem a
    # allow-list/gates (as funcoes de modulo ja os aplicam). Assinaturas
    # identicas as funcoes -> chamadas por posicao ou keyword funcionam.
    def fs_read(self, path, max_bytes=200_000):
        return fs_read(path, max_bytes)

    def fs_write(self, path, content, append=False):
        return fs_write(path, content, append)

    def fs_list(self, path, glob="*", recursive=False, limit=200):
        return fs_list(path, glob, recursive, limit)

    def fs_stat(self, path):
        return fs_stat(path)

    def fs_search(self, root, pattern, regex=False, limit=50):
        return fs_search(root, pattern, regex, limit)

    def fs_move(self, src, dst):
        return fs_move(src, dst)

    def run_shell(self, cmd, cwd=None, timeout=60):
        return run_shell(cmd, cwd, timeout)

    def run_python(self, code, timeout=60):
        return run_python(code, timeout)

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "fs_read",
                "description": "Le um arquivo texto (UTF-8). Restrito a allow-list.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Caminho absoluto ou relativo"},
                        "max_bytes": {"type": "integer", "default": 200000},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "fs_write",
                "description": "Escreve ou anexa em arquivo (UTF-8).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "append": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "fs_list",
                "description": "Lista diretorio com glob.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "glob": {"type": "string", "default": "*"},
                        "recursive": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "default": 200},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "fs_stat",
                "description": "Metadados de arquivo/diretorio.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "fs_search",
                "description": "Grep recursivo (substring ou regex).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "root": {"type": "string"},
                        "pattern": {"type": "string"},
                        "regex": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "default": 50},
                    },
                    "required": ["root", "pattern"],
                },
            },
            {
                "name": "run_shell",
                "description": "Executa comando shell. Bloqueia comandos perigosos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cmd": {"type": "string"},
                        "cwd": {"type": "string"},
                        "timeout": {"type": "integer", "default": 60},
                    },
                    "required": ["cmd"],
                },
            },
            {
                "name": "run_python",
                "description": "Executa snippet Python em subprocess isolado.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "timeout": {"type": "integer", "default": 60},
                    },
                    "required": ["code"],
                },
            },
        ]

    def health(self) -> dict:
        return {
            "status": "ok",
            "allowlist": [str(p) for p in ALLOWLIST],
            "tools": 7,
        }
