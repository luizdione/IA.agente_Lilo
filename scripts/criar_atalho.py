"""Cria o atalho "LILO" na Area de Trabalho do Windows.

Rode NA MAQUINA WINDOWS (nao no CI/Linux):

    python scripts\\criar_atalho.py              # icone abre o CHAT NO NAVEGADOR
    python scripts\\criar_atalho.py --terminal   # icone abre o REPL no PowerShell

v13.7 (decisao do dono, 26/08): o duplo clique abre uma janela PowerShell
rodando `lilo web` — o servidor local sobe e o NAVEGADOR abre sozinho em
http://localhost:8100 com o chat (mesmo loop/portao do terminal). A flag
--terminal regrava o atalho para o comportamento v13.5 (so o REPL).
Icone: lilo_icon.ico. Usa [Environment]::GetFolderPath('Desktop'), entao
respeita Desktop redirecionado pelo OneDrive.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if os.name != "nt":
        print("Este script cria um atalho .lnk do WINDOWS.")
        print("Rode na sua maquina: python scripts\\criar_atalho.py")
        return 1

    terminal = "--terminal" in sys.argv
    ps1 = ROOT / "lilo.ps1"
    ico = ROOT / "lilo_icon.ico"
    if not ps1.exists():
        print("[ERRO] lilo.ps1 nao encontrado em %s" % ROOT)
        return 1

    # PowerShell: resolve a Area de Trabalho real e grava o .lnk via COM.
    # Default: lilo.ps1 web (sobe o servidor e abre o navegador);
    # --terminal: lilo.ps1 puro (REPL na propria janela).
    argumentos = '-NoExit -ExecutionPolicy Bypass -File \"%s\"%s' % (
        ps1, "" if terminal else " web")
    descricao = ("LILO — agente de IA local (Ollama) no terminal" if terminal
                 else "LILO — agente de IA local (Ollama) no navegador")
    ps = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\\LILO.lnk\");"
        "$s.TargetPath='powershell.exe';"
        "$s.Arguments='%s';"
        "$s.WorkingDirectory='%s';"
        "$s.IconLocation='%s';"
        "$s.Description='%s';"
        "$s.Save();"
        "Write-Output \"$d\\LILO.lnk\""
    ) % (argumentos, ROOT, ico if ico.exists() else ps1, descricao)

    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        print("[ERRO] PowerShell falhou:\n" + (r.stderr or r.stdout))
        return 1
    print("Atalho criado: " + r.stdout.strip())
    if terminal:
        print("Duplo clique nele abre o LILO no terminal (REPL).")
    else:
        print("Duplo clique nele sobe o servidor e abre o CHAT no navegador "
              "(http://localhost:8100).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
