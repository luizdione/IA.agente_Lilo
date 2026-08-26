"""Cria o atalho "LILO" na Area de Trabalho do Windows.

Rode NA MAQUINA WINDOWS (nao no CI/Linux):

    python scripts\\criar_atalho.py

v13.5: o duplo clique abre uma janela POWERSHELL rodando o REPL do LILO
(via lilo.ps1 da raiz; -NoExit mantem a janela viva ao sair do REPL). Nao
existe dashboard de navegador no v13 — o terminal E a interface. Icone:
lilo_icon.ico. Usa [Environment]::GetFolderPath('Desktop'), entao respeita
Desktop redirecionado pelo OneDrive.
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

    ps1 = ROOT / "lilo.ps1"
    ico = ROOT / "lilo_icon.ico"
    if not ps1.exists():
        print("[ERRO] lilo.ps1 nao encontrado em %s" % ROOT)
        return 1

    # PowerShell: resolve a Area de Trabalho real e grava o .lnk via COM.
    # Alvo = powershell.exe rodando o lilo.ps1 (janela de TERMINAL, por design).
    ps = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\\LILO.lnk\");"
        "$s.TargetPath='powershell.exe';"
        "$s.Arguments='-NoExit -ExecutionPolicy Bypass -File \"%s\"';"
        "$s.WorkingDirectory='%s';"
        "$s.IconLocation='%s';"
        "$s.Description='LILO — agente de IA local (Ollama) no terminal';"
        "$s.Save();"
        "Write-Output \"$d\\LILO.lnk\""
    ) % (ps1, ROOT, ico if ico.exists() else ps1)

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
