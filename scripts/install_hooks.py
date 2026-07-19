#!/usr/bin/env python
"""
scripts/install_hooks.py
========================
Instala hooks do Git para o repositorio LILO.

Hook instalado:
- pre-commit -> chama scripts/pre_commit_ast_check.py

Cross-platform: cria um wrapper shell ou .bat conforme o sistema.

Uso:
    python scripts/install_hooks.py
    python scripts/install_hooks.py --uninstall
"""

from __future__ import annotations

import stat
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = _ROOT / ".git" / "hooks"
HOOK_NAME = "pre-commit"


# Hook shell (Linux/macOS/Git-Bash no Windows)
SHELL_HOOK = """#!/usr/bin/env bash
# pre-commit instalado por scripts/install_hooks.py
# Bloqueia commit se houver .py com SyntaxError ou truncamento OneDrive.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
python "$SCRIPT_DIR/scripts/pre_commit_ast_check.py"
"""

# Para Windows nativo (cmd.exe), Git tambem aceita .bat dentro de hooks/
# se o nome for pre-commit (sem extensao) com shebang Windows-friendly.
# Na pratica, Git for Windows roda hooks via Git-Bash (sh.exe), entao
# um shell script com shebang #!/usr/bin/env bash funciona. Mantemos
# uma copia .bat ao lado para diagnostico manual.
BAT_HOOK = """@echo off
REM diagnostico: roda o validador AST manualmente
python "%~dp0\\..\\..\\scripts\\pre_commit_ast_check.py"
"""


def install() -> int:
    if not HOOKS_DIR.exists():
        print(f"[install_hooks] {HOOKS_DIR} nao existe -- repo nao inicializado?",
              file=sys.stderr)
        return 1
    target = HOOKS_DIR / HOOK_NAME
    target.write_text(SHELL_HOOK, encoding="utf-8", newline="\n")
    # chmod +x (no-op no Windows, mas explicito)
    try:
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass

    bat_target = HOOKS_DIR / (HOOK_NAME + "_diag.bat")
    bat_target.write_text(BAT_HOOK, encoding="utf-8", newline="\r\n")

    print(f"[install_hooks] OK")
    print(f"  hook ativo:    {target}")
    print(f"  diag manual:   {bat_target}")
    print(f"  validador:     scripts/pre_commit_ast_check.py")
    print()
    print("Teste: edite um .py, faca git add, e tente commit.")
    print("Bypass de emergencia: git commit --no-verify")
    return 0


def uninstall() -> int:
    target = HOOKS_DIR / HOOK_NAME
    bat_target = HOOKS_DIR / (HOOK_NAME + "_diag.bat")
    removed = 0
    for p in (target, bat_target):
        if p.exists():
            p.unlink()
            print(f"[install_hooks] removido {p}")
            removed += 1
    if removed == 0:
        print("[install_hooks] nenhum hook instalado para remover")
    return 0


def main() -> int:
    if "--uninstall" in sys.argv[1:]:
        return uninstall()
    return install()


if __name__ == "__main__":
    sys.exit(main())
