"""Pytest configuration -- adiciona raiz do projeto ao sys.path.

Permite `from lilo import ...` mesmo executando `pytest` a partir de
subpastas. Mantem o autoskip de testes que exigem Ollama/GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


class FakeOllama:
    """Transporte fake p/ ClienteOllama: fila de respostas roteirizadas +
    gravacao dos payloads enviados. Um item Exception e LEVANTADO (simula
    erro de rede/HTTP); um dict e retornado como resposta do servidor."""

    def __init__(self, respostas=None):
        self.respostas = list(respostas or [])
        self.chamadas = []  # [(url, payload), ...]

    def __call__(self, url, payload):
        import copy
        self.chamadas.append((url, copy.deepcopy(payload)))
        if not self.respostas:
            raise AssertionError("FakeOllama: fila de respostas vazia")
        item = self.respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def resposta_texto(texto):
    """Resposta /api/chat sem tool_calls (= resposta final)."""
    return {"message": {"role": "assistant", "content": texto},
            "done_reason": "stop"}


def resposta_tools(*calls):
    """Resposta /api/chat com tool_calls: calls = (nome, args_dict|str)."""
    return {"message": {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": n, "arguments": a}} for n, a in calls]},
        "done_reason": "stop"}


@pytest.fixture
def fake_ollama():
    return FakeOllama


@pytest.fixture(autouse=True)
def _sem_sleep_no_retry(monkeypatch):
    """Backoff do cliente nao dorme de verdade nos testes."""
    try:
        import lilo.cliente as _c
        monkeypatch.setattr(_c.time, "sleep", lambda s: None)
    except ImportError:
        pass


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
