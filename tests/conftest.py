"""Pytest da v14: raiz do repo no sys.path (`from lilo_host import ...` de qualquer pasta).

A suite roda sem Ollama, GPU, Docker, R ou WSL: o que depende deles pula sozinho
(`skipif`/`importorskip` nos proprios testes). O portao de latencia e `lilo.ps1 bench`.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
