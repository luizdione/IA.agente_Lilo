"""
agents/desktop/composed.py -- Tools compostas (LILO Desktop Commander+)
=======================================================================
Tools que combinam multiplas operacoes do Desktop Commander em uma unica
chamada MCP. O objetivo e reduzir o numero de round-trips Claude<->MCP e,
por consequencia, o consumo de tokens em fluxos que envolvem ler/buscar
varios arquivos antes de decidir uma acao.

Quando uma das tools encontrar algo fora da allow-list, ela retorna apenas
a string de erro para aquele item -- os demais continuam sendo processados,
permitindo que o LLM aprenda exatamente o que falhou em uma so resposta.

Funcoes:
    fs_batch_read(paths, max_bytes_each)        -> dict (path -> conteudo)
    fs_codemod(path, find, replace, regex, ...) -> diff resumido + count
    grep_and_read(root, pattern, ...)           -> matches com contexto
    process_run_and_wait(cmd, cwd, ...)         -> stdout+stderr+exit
"""

from __future__ import annotations

import re
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from agents.desktop.agent import (
    _is_path_allowed,
    _is_cmd_dangerous,
    fs_read as _fs_read,
)


def fs_batch_read(paths: list, max_bytes_each: int = 100_000) -> str:
    """Le varios arquivos em uma unica chamada MCP. Retorna JSON com cada
    path como chave e o conteudo (ou erro) como valor. Ideal para o LLM
    "carregar contexto" sem N round-trips."""
    out = {}
    for p in paths:
        try:
            content = _fs_read(p, max_bytes_each)
            out[p] = content
        except Exception as e:
            out[p] = f"[ERRO leitura] {e}"
    # Header com sumario para o LLM saber rapidamente o que veio.
    summary = {
        "_summary": {
            "n_paths": len(paths),
            "n_errors": sum(1 for v in out.values() if v.startswith("[ERRO")),
            "total_bytes": sum(len(v) for v in out.values()
                               if not v.startswith("[ERRO")),
        },
        "files": out,
    }
    return json.dumps(summary, ensure_ascii=False)


def fs_codemod(path: str, find: str, replace: str,
               regex: bool = False, count: int = 0) -> str:
    """Find-and-replace dentro de UM arquivo de texto (UTF-8). Retorna
    quantos matches foram substituidos + os primeiros 5 trechos modificados
    para o LLM verificar a sanidade. Nao toca em arquivos binarios.

    count=0 substitui todos; count=N substitui no maximo N ocorrencias.
    Equivale ao edit_block do Desktop Commander quando regex=False.
    """
    p = Path(path)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.is_file():
        return f"[ERRO] nao e arquivo: {path}"
    try:
        original = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[ERRO] arquivo nao e texto UTF-8: {path}"
    if regex:
        pattern = re.compile(find, re.MULTILINE)
        n = len(pattern.findall(original))
        if count > 0:
            new_text = pattern.sub(replace, original, count=count)
            applied = min(n, count)
        else:
            new_text = pattern.sub(replace, original)
            applied = n
    else:
        n = original.count(find)
        if count > 0:
            new_text = original.replace(find, replace, count)
            applied = min(n, count)
        else:
            new_text = original.replace(find, replace)
            applied = n
    if applied == 0:
        return f"[NO-OP] pattern nao encontrado em {path}"
    p.write_text(new_text, encoding="utf-8")
    # Resumo dos primeiros 5 trechos alterados (para validar visualmente).
    samples = []
    if not regex:
        for i, line in enumerate(new_text.splitlines(), 1):
            if replace and replace in line:
                samples.append(f"L{i}: {line.strip()[:120]}")
                if len(samples) >= 5:
                    break
    return (
        f"[OK] {applied} substituicao(oes) em {path}\n"
        f"--- amostras ({len(samples)}) ---\n" + "\n".join(samples)
    )


def grep_and_read(root: str, pattern: str, regex: bool = False,
                  context_lines: int = 3, limit: int = 20) -> str:
    """Busca recursiva + retorna o trecho com N linhas de contexto antes/
    depois de cada match. Substitui o ciclo `fs_search -> fs_read x N`.

    Retorna texto formatado: path:linha + (2*context_lines + 1) linhas.
    """
    p = Path(root)
    ok, why = _is_path_allowed(p)
    if not ok:
        return f"[ERRO] {why}"
    if not p.is_dir():
        return f"[ERRO] nao e diretorio: {root}"
    matcher = re.compile(pattern) if regex else None
    blocks = []
    for f in p.rglob("*"):
        if not f.is_file():
            continue
        # Pular binarios obvios pelo nome
        if f.suffix.lower() in (".pyc", ".so", ".dll", ".exe", ".png",
                                ".jpg", ".jpeg", ".pdf", ".zip", ".gz",
                                ".tar", ".whl", ".db"):
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            hit = (matcher.search(line) if matcher else (pattern in line))
            if not hit:
                continue
            lo = max(0, i - context_lines)
            hi = min(len(lines), i + context_lines + 1)
            ctx = "\n".join(lines[lo:hi])
            blocks.append(f"=== {f}:{i+1} ===\n{ctx}")
            if len(blocks) >= limit:
                return "\n\n".join(blocks)
    return "\n\n".join(blocks) if blocks else "(sem matches)"


def process_run_and_wait(cmd: str, cwd: Optional[str] = None,
                         timeout: int = 120,
                         capture_output: bool = True) -> str:
    """Executa um processo, aguarda terminar e retorna stdout+stderr+exit.
    Comportamento equivalente ao par `start_process + interact_with_process`
    do Desktop Commander quando voce sabe que o processo termina sozinho
    (build, teste, lint, script CLI). Para processos longos/REPL, prefira
    `run_shell` com timeout maior.
    """
    danger = _is_cmd_dangerous(cmd)
    if danger:
        return f"[ERRO] comando perigoso bloqueado (pattern: {danger})"
    if cwd:
        ok, why = _is_path_allowed(Path(cwd))
        if not ok:
            return f"[ERRO] cwd: {why}"
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=capture_output, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        if not capture_output:
            return f"[exit={r.returncode}] (stdout/stderr nao capturados)"
        out = (r.stdout or "")[:16000]  # mais espaco do que run_shell
        err = (r.stderr or "")[:4000]
        return (
            f"[exit={r.returncode}] cmd={cmd!r}\n"
            f"--- STDOUT ---\n{out}\n"
            f"--- STDERR ---\n{err}"
        )
    except subprocess.TimeoutExpired:
        return f"[ERRO] timeout apos {timeout}s"
    except Exception as e:
        return f"[ERRO] {e}"
