"""Atalhos do LILO no Windows: Area de Trabalho e Inicializacao.

    python scripts\\criar_atalho.py                  # Area de Trabalho: LILO.lnk -> lilo.ps1 abrir
    python scripts\\criar_atalho.py --inicializacao  # + Inicializacao: lilo.ps1 inicio (sem janela)
    python scripts\\criar_atalho.py --remover        # apaga os dois

Area de Trabalho: a janela do PowerShell fica aberta (-NoExit) para mostrar o
aquecimento e eventuais erros; abre o navegador em http://127.0.0.1:3000.
Inicializacao (shell:startup): roda no logon, sem janela, e grava tudo em
%LOCALAPPDATA%\\LILO\\bench\\inicio.log. Respeita o interruptor de GPU (com ele
em off nao carrega nada) e espera o Ollama e o Docker Desktop subirem (ate 3 min).
Usa [Environment]::GetFolderPath, entao respeita Desktop redirecionado pelo OneDrive.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PS1 = ROOT / "lilo.ps1"
ICO = ROOT / "lilo_icon.ico"

# pasta especial -> (argumentos do powershell.exe, descricao, janela: 1 normal, 7 minimizada)
ATALHOS = {
    "Desktop": ('-NoExit -ExecutionPolicy Bypass -File "%s" abrir' % PS1,
                "LILO - chat local (Ollama + Open WebUI)", 1),
    "Startup": ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%s" inicio' % PS1,
                "LILO - sobe a interface e aquece o modelo no logon", 7),
}

# Grava o .lnk via COM. Placeholders: pasta, argumentos, pasta de trabalho, icone, descricao, janela.
_CRIAR = r"""
$d=[Environment]::GetFolderPath('%s');
$s=(New-Object -ComObject WScript.Shell).CreateShortcut("$d\LILO.lnk");
$s.TargetPath='powershell.exe';
$s.Arguments='%s';
$s.WorkingDirectory='%s';
$s.IconLocation='%s';
$s.Description='%s';
$s.WindowStyle=%d;
$s.Save();
Write-Output "$d\LILO.lnk"
"""
_REMOVER = r"""
$p=Join-Path ([Environment]::GetFolderPath('%s')) 'LILO.lnk';
if (Test-Path $p) { Remove-Item $p; Write-Output "removido $p" } else { Write-Output "nao havia $p" }
"""


def _powershell(script: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        sys.exit("[ERRO] PowerShell falhou:\n" + (r.stderr or r.stdout))
    return r.stdout.strip()


def criar(pasta: str) -> str:
    argumentos, descricao, janela = ATALHOS[pasta]
    return _powershell(_CRIAR % (pasta, argumentos, ROOT, ICO if ICO.exists() else PS1,
                                 descricao, janela))


def remover(pasta: str) -> str:
    return _powershell(_REMOVER % pasta)


def main() -> int:
    if os.name != "nt":
        print("Este script cria atalhos .lnk do WINDOWS; rode na sua maquina.")
        return 1
    if not PS1.exists():
        print("[ERRO] lilo.ps1 nao encontrado em %s" % ROOT)
        return 1
    if "--remover" in sys.argv:
        for pasta in ATALHOS:
            print(remover(pasta))
        return 0
    pastas = ["Desktop"] + (["Startup"] if "--inicializacao" in sys.argv else [])
    for pasta in pastas:
        print("Atalho criado: " + criar(pasta))
    if "Startup" in pastas:
        print("No proximo logon o LILO sobe sozinho (log: %LOCALAPPDATA%\\LILO\\bench\\inicio.log).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
