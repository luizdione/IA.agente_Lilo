#!/usr/bin/env python
"""
scripts/pre_commit_ast_check.py
================================
Valida arquivos .py modificados antes do commit usando ast.parse().

Detecta especificamente o problema de TRUNCAMENTO do OneDrive
(arquivos que aparecem completos no editor mas chegam truncados ao
Git/sandbox), via duas heuristicas:

  1) ast.parse() falha -- sintaxe quebrada por truncamento.
  2) Arquivo termina sem newline final E sem fechar string/bracket
     aberto na ultima linha visivel.

Uso direto (CLI):
    python scripts/pre_commit_ast_check.py [arquivo.py ...]

Sem argumentos: pega todos os .py em git diff --cached --name-only.

Bypass: rode `git commit --no-verify` para pular este hook em uma
emergencia (mas registre o motivo).

Codigos de saida:
    0 -- todos OK
    1 -- pelo menos um arquivo invalido
    2 -- erro de configuracao (git nao encontrado, etc.)
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


COLOR = sys.stdout.isatty() and os.name != "nt"
RED = "\033[31m" if COLOR else ""
GREEN = "\033[32m" if COLOR else ""
YELLOW = "\033[33m" if COLOR else ""
RESET = "\033[0m" if COLOR else ""


def _staged_python_files() -> list[Path]:
    """Lista .py que estao staged para o commit atual."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            text=True, encoding="utf-8", errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"{RED}[pre-commit-ast] git nao disponivel: {e}{RESET}",
              file=sys.stderr)
        sys.exit(2)
    return [Path(line) for line in out.splitlines()
            if line.strip() and line.endswith(".py")]


def _looks_truncated(text: str) -> str | None:
    """Heuristica para detectar truncamento do OneDrive.

    Retorna mensagem descrevendo o problema, ou None se OK.
    """
    if not text:
        return "arquivo vazio"
    # 1) Null bytes -> sync corrompido
    if "\x00" in text:
        return "contem null bytes (sync OneDrive corrompido)"
    # 2) Bracket counter simples
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    in_str = False
    str_quote = ""
    triple = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt3 = text[i:i + 3]
        if not in_str:
            if nxt3 in ('"""', "'''"):
                in_str = True
                triple = True
                str_quote = nxt3
                i += 3
                continue
            if ch in ('"', "'"):
                in_str = True
                triple = False
                str_quote = ch
                i += 1
                continue
            if ch == "#":
                # comentario: pula ate \n
                nl = text.find("\n", i)
                i = len(text) if nl == -1 else nl
                continue
            if ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values():
                if stack and stack[-1] == ch:
                    stack.pop()
        else:
            if triple:
                if nxt3 == str_quote:
                    in_str = False
                    triple = False
                    i += 3
                    continue
            else:
                if ch == "\\":
                    i += 2
                    continue
                if ch == str_quote:
                    in_str = False
                if ch == "\n" and not triple:
                    # string single-line nao fechou na linha -> SyntaxError
                    # ast vai pegar; nao geramos warning duplicado
                    in_str = False
        i += 1
    if in_str:
        return f"string aberta nao fechada (delimiter={str_quote!r})"
    if stack:
        return f"brackets nao fechados: {''.join(stack[::-1])}"
    return None


def validate(path: Path) -> tuple[bool, str]:
    """Valida um arquivo. Retorna (ok, mensagem_diagnostica)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")
    except FileNotFoundError:
        return False, f"arquivo nao existe: {path}"
    except Exception as e:
        return False, f"erro ao ler: {e}"

    trunc = _looks_truncated(text)
    if trunc:
        return False, f"truncamento provavel -- {trunc}"

    try:
        ast.parse(text, filename=str(path))
    except SyntaxError as e:
        line = e.lineno or "?"
        col = e.offset or "?"
        return False, f"SyntaxError linha {line}:{col} -- {e.msg}"
    except Exception as e:
        return False, f"erro inesperado no ast.parse: {e}"
    return True, "ok"


def check(paths: Iterable[Path]) -> int:
    paths = list(paths)
    if not paths:
        print(f"{GREEN}[pre-commit-ast] nenhum .py staged. OK.{RESET}")
        return 0

    failures: list[tuple[Path, str]] = []
    print(f"[pre-commit-ast] validando {len(paths)} arquivo(s) Python...")
    for p in paths:
        ok, msg = validate(p)
        if ok:
            print(f"  {GREEN}OK{RESET}    {p}")
        else:
            print(f"  {RED}FAIL{RESET}  {p}  ({msg})")
            failures.append((p, msg))

    if failures:
        print()
        print(f"{RED}[pre-commit-ast] commit BLOQUEADO -- "
              f"{len(failures)} arquivo(s) invalido(s):{RESET}")
        for p, msg in failures:
            print(f"  - {p}: {msg}")
        print()
        print(f"{YELLOW}Para emergencias, use: git commit --no-verify{RESET}")
        print(f"{YELLOW}(documente o motivo na mensagem do commit){RESET}")
        return 1

    print(f"{GREEN}[pre-commit-ast] todos OK.{RESET}")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        paths = [Path(a) for a in sys.argv[1:]]
    else:
        paths = _staged_python_files()
    return check(paths)


if __name__ == "__main__":
    sys.exit(main())
