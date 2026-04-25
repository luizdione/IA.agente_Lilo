"""
ollama_client.py
Comunicação com modelos locais via Ollama API (localhost:11434).
"""

import requests
import json
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"


def check_ollama_status() -> dict:
    """Verifica se o Ollama está rodando e lista modelos disponíveis."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return {"online": True, "models": models}
    except requests.ConnectionError:
        pass
    return {"online": False, "models": []}


def generate(
    prompt: str,
    model: str = "llama3.1:8b",
    system: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """
    Envia prompt ao Ollama e retorna a resposta completa (modo não-streaming).
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=300,  # PDFs longos podem demorar
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.ConnectionError:
        raise RuntimeError(
            "Ollama não está rodando. Execute 'ollama serve' no terminal."
        )
    except requests.Timeout:
        raise RuntimeError("Timeout na geração. Tente reduzir o tamanho do texto.")


def generate_with_image(
    prompt: str,
    image_base64: str,
    model: str = "llava:13b",
    temperature: float = 0.3,
) -> str:
    """
    Envia prompt + imagem (base64) para modelo multimodal (ex: LLaVA).
    Usado para interpretar gráficos extraídos de PDFs.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
        },
    }

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.ConnectionError:
        raise RuntimeError("Ollama não está rodando.")
    except Exception as e:
        raise RuntimeError(f"Erro na análise de imagem: {e}")
