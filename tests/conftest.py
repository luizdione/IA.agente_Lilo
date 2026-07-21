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


# V16: pula automaticamente testes marcados que precisam de backend ausente.
# Marque com @pytest.mark.requires_ollama / @pytest.mark.requires_gpu.
def _ollama_up() -> bool:
    import os
    try:
        import requests
        url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        requests.get(url + "/api/tags", timeout=1.0)
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    import os
    import pytest
    ollama_ok = _ollama_up()
    skip_gpu_env = os.getenv("LILO_SKIP_GPU", "").strip().lower() not in ("", "0", "false", "no")
    sk_ollama = pytest.mark.skip(reason="Ollama indisponivel (localhost:11434)")
    sk_gpu = pytest.mark.skip(reason="GPU/Ollama ausente ou LILO_SKIP_GPU=1")
    for item in items:
        if "requires_ollama" in item.keywords and not ollama_ok:
            item.add_marker(sk_ollama)
        if "requires_gpu" in item.keywords and (skip_gpu_env or not ollama_ok):
            item.add_marker(sk_gpu)
