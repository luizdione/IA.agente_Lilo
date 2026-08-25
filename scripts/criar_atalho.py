"""Cria o atalho "LILO" na Area de Trabalho do Windows.

Rode NA MAQUINA WINDOWS (nao no CI/Linux):

    python scripts\\criar_atalho.py

O atalho aponta para o lilo.bat da raiz do repo (duplo clique abre o REPL),
com o icone lilo_icon.ico. Usa [Environment]::GetFolderPath('Desktop') via
PowerShell, entao respeita Desktop redirecionado pelo OneDrive.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if os.name != "nt":
        print("Este script cria um atalho .lnk do WINDOWS.")
        print("Rode na sua maquina: python scripts\\criar_atalho.py")
        return 1

    bat = ROOT / "lilo.bat"
    ico = ROOT / "lilo_icon.ico"
    if not bat.exists():
        print("[ERRO] lilo.bat nao encontrado em %s" % ROOT)
        return 1

    # PowerShell: resolve a Area de Trabalho real e grava o .lnk via COM.
    ps = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\\LILO.lnk\");"
        "$s.TargetPath='%s';"
        "$s.WorkingDirectory='%s';"
        "$s.IconLocation='%s';"
        "$s.Description='LILO — agente de IA local (Ollama)';"
        "$s.Save();"
        "Write-Output \"$d\\LILO.lnk\""
    ) % (bat, ROOT, ico if ico.exists() else bat)

    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        print("[ERRO] PowerShell falhou:\n" + (r.stderr or r.stdout))
        return 1
    print("Atalho criado: " + r.stdout.strip())
    print("Duplo clique nele abre o LILO no terminal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
