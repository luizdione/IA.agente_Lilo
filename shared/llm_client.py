"""
shared/llm_client.py — Cliente LLM único para todos os subagentes LILO.

Prioridade de roteamento:
  1. LiteLLM Proxy (llm-gateway na porta 4000) — se disponível
  2. Ollama direto (porta 11434) — fallback local
  3. Anthropic Claude via API — se ANTHROPIC_API_KEY definida

Uso:
    from shared.llm_client import get_client
    client = get_client()
    resposta = client.chat("Explique PCR em termos simples.")
"""

import os
import json
import requests
from typing import Optional
from .logger import get_logger
from .utils import load_env, get_env

load_env()
log = get_logger("LLMClient")

# ── Configurações lidas do ambiente ──────────────────────────────────────────
LITELLM_URL   = get_env("LITELLM_PROXY_URL",    "http://localhost:4000")
OLLAMA_URL    = get_env("OLLAMA_HOST",           "http://localhost:11434")
ANTHROPIC_KEY = get_env("ANTHROPIC_API_KEY",     "")
TIMEOUT       = int(get_env("LLM_TIMEOUT",       "120"))

# Modelos por papel (nomes exatos do `ollama list`)
MODELS = {
    "chat":         get_env("OLLAMA_MODEL",       "llama3.1:8b-instruct-q8_0"),
    "code":         get_env("OLLAMA_MODEL_CODE",  "qwen2.5-coder:14b"),
    "plan":         get_env("OLLAMA_MODEL_PLAN",  "phi3:14b-medium-128k-instruct-q4_K_M"),
    "autocomplete": get_env("OLLAMA_MODEL_FAST",  "qwen2.5-coder:7b-instruct"),
    "embed":        get_env("OLLAMA_MODEL_EMBED",  "mxbai-embed-large:latest"),
}
DEFAULT_MODEL = MODELS["chat"]


class LLMClient:
    """
    Cliente unificado que abstrai LiteLLM, Ollama e Anthropic.
    Use get_client() para obter a instância singleton.
    """

    def __init__(self):
        self._backend: Optional[str] = None  # lazy — detecta no primeiro uso

    @property
    def backend(self) -> str:
        if self._backend is None:
            self._backend = self._detect_backend()
            log.info(f"Backend ativo: {self._backend}")
        return self._backend

    # ── Detecção de backend ──────────────────────────────────────────────────

    def _detect_backend(self) -> str:
        """Detecta qual backend está disponível (timeout reduzido)."""
        # 1. Ollama (prioridade — mais comum no setup local)
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.0)
            if r.status_code == 200:
                return "ollama"
        except Exception:
            pass

        # 2. LiteLLM Proxy (só tenta se URL não é default ou se Ollama falhou)
        try:
            r = requests.get(f"{LITELLM_URL}/health", timeout=1.0)
            if r.status_code == 200:
                return "litellm"
        except Exception:
            pass

        # 3. Anthropic (cloud — sem probe de rede)
        if ANTHROPIC_KEY:
            return "anthropic"

        log.warning("Nenhum backend LLM disponível! Respostas serão mock.")
        return "mock"

    # ── Interface pública ────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: str = "Você é o LILO, um assistente de IA especializado em bioinformática e ciência de dados. Responda em português brasileiro.",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        tier: Optional[str] = None,
    ) -> str:
        """
        Envia prompt e retorna resposta em texto.

        Se tier for especificado (da PolicyEngine), roteia para o backend correto:
          - "ollama*" → Ollama local
          - "claude_sonnet" / "claude_opus" → Anthropic API com modelo específico
          - None → usa detecção automática de backend
        """
        # Roteamento por tier (Policy Engine)
        if tier and tier.startswith("claude_"):
            claude_models = {
                "claude_sonnet": "claude-sonnet-4-20250514",
                "claude_opus": "claude-opus-4-20250514",
            }
            claude_model = claude_models.get(tier, "claude-sonnet-4-20250514")
            log.info(f"Tier {tier} → Anthropic API ({claude_model})")
            return self._chat_anthropic(prompt, system, temperature, max_tokens, model=claude_model)

        if tier and tier.startswith("ollama"):
            model = model or DEFAULT_MODEL
            log.info(f"Tier {tier} → Ollama ({model})")
            return self._chat_ollama(prompt, system, model, temperature, max_tokens)

        # Sem tier → auto-detect (comportamento original)
        model = model or DEFAULT_MODEL

        if self.backend == "litellm":
            return self._chat_litellm(prompt, system, model, temperature, max_tokens)
        elif self.backend == "ollama":
            return self._chat_ollama(prompt, system, model, temperature, max_tokens)
        elif self.backend == "anthropic":
            return self._chat_anthropic(prompt, system, temperature, max_tokens)
        else:
            return f"[MOCK] Backend indisponível. Prompt recebido: {prompt[:100]}"

    def list_models(self) -> list[str]:
        """Lista modelos disponíveis no backend ativo."""
        try:
            if self.backend == "litellm":
                r = requests.get(f"{LITELLM_URL}/models", timeout=5)
                return [m["id"] for m in r.json().get("data", [])]
            elif self.backend == "ollama":
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
                return [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            log.error(f"Erro ao listar modelos: {e}")
        return []

    def health(self) -> dict:
        """Retorna status do cliente."""
        return {
            "backend": self.backend,
            "litellm_url": LITELLM_URL,
            "ollama_url": OLLAMA_URL,
            "default_model": DEFAULT_MODEL,
            "anthropic_configured": bool(ANTHROPIC_KEY),
        }

    # ── Implementações por backend ───────────────────────────────────────────

    def _chat_litellm(self, prompt, system, model, temperature, max_tokens) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {get_env('LITELLM_API_KEY', 'sk-litellm-local-dev')}"}
        r = requests.post(f"{LITELLM_URL}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _chat_ollama(self, prompt, system, model, temperature, max_tokens) -> str:
        # Usa /api/chat (formato messages)
        payload = {
            "model": model,
            "messages": [
                {"role": "system",    "content": system},
                {"role": "user",      "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_gpu": 99,    # offload todos os layers para GPU (RTX 3060)
                "num_thread": 8,  # threads CPU para camadas residuais
            },
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def _chat_anthropic(self, prompt, system, temperature, max_tokens, model=None) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        model = model or "claude-sonnet-4-20250514"
        log.info(f"Anthropic API → {model}")
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return msg.content[0].text


# ── Singleton ────────────────────────────────────────────────────────────────
_client_instance: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """Retorna instância singleton do LLMClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
