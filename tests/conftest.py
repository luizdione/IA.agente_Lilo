"""Pytest configuration -- adiciona raiz do projeto ao sys.path.

Permite `from shared.kv_memory import ...` mesmo executando `pytest` a
partir de subpastas.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Raiz do repo = ../ relativo a este arquivo (tests/conftest.py)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
