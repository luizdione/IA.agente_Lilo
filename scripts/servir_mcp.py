"""Lancador do `lilo mcp-serve` SEM hifens na linha de comando (v13.10).

Por que existe: o `claude mcp add` recebe o comando do servidor depois de
`--`, e esse separador nem sempre sobrevive ao shell/shim (no PowerShell 5.1
do dono ele sumiu e o `-m` de `python -m lilo mcp-serve` virou
"unknown option '-m'"). Com este lancador o comando registrado fica
`<python> <...>\\scripts\\servir_mcp.py` — nenhum token comeca com `-`, entao
o registro funciona com ou sem o separador, em qualquer shell.

Irmao do lilo.bat/lilo.ps1: zero logica propria, so chama o MESMO subcomando.
Funciona mesmo sem `pip install -e .` (poe a raiz do repo no sys.path).
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from lilo.cli import main  # noqa: E402 — precisa do sys.path acima

raise SystemExit(main(["mcp-serve"] + sys.argv[1:]))
