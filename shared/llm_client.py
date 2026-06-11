"""
shared/llm_client.py -- Cliente LLM unico para todos os subagentes LILO.

Prioridade de roteamento:
  1. LiteLLM Proxy (config/litellm_config.yaml na porta 4000) -- se disponivel
  2. Ollama direto (porta 11434) -- fallback local
  3. Anthropic Claude via API -- se ANTHROPIC_API_KEY definida

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

LITELLM_URL   = get_env("LITELLM_PROXY_URL",    "http://localhost:4000")
OLLAMA_URL    = get_env("OLLAMA_HOST",           "http://localhost:11434")
ANTHROPIC_KEY = get_env("ANTHROPIC_API_KEY",     "")
TIMEOUT       = int(get_env("LLM_TIMEOUT",       "300"))

MODELS = {
    "chat":         get_env("OLLAMA_MODEL",       "llama3.1:8b-instruct-q8_0"),
    "code":         get_env("OLLAMA_MODEL_CODE",  "qwen2.5-coder:14b"),
    "plan":         get_env("OLLAMA_MODEL_PLAN",  "phi3:14b-medium-128k-instruct-q4_K_M"),
    "autocomplete": get_env("OLLAMA_MODEL_FAST",  "qwen2.5-coder:7b-instruct"),
    "embed":        get_env("OLLAMA_MODEL_EMBED",  "mxbai-embed-large:latest"),
}
DEFAULT_MODEL = MODELS["chat"]

# System prompt padrao para nivel PhD
DEFAULT_SYSTEM = (
    "Voce e o LILO, assistente de IA para um PhD em Biologia Molecular "
    "e Cientista de Dados senior. Use terminologia tecnica precisa, "
    "nao simplifique. Responda em portugues brasileiro com rigor cientifico."
)


class LLMClient:
    """
    Cliente unificado que abstrai LiteLLM, Ollama e Anthropic.
    Use get_client() para obter a instancia singleton.
    """

    def __init__(self):
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            self._backend = self._detect_backend()
            log.info("Backend ativo: %s", self._backend)
        return self._backend

    def _detect_backend(self):
        """Detecta qual backend esta disponivel.
        Ordem alinhada com docstring do modulo (2026-05-06):
          1. LiteLLM Proxy (unifica modelos + observabilidade)
          2. Ollama direto (fallback local)
          3. Anthropic Claude
        """
        try:
            r = requests.get(LITELLM_URL + "/health", timeout=1.0)
            if r.status_code == 200:
                return "litellm"
        except Exception:
            pass
        try:
            r = requests.get(OLLAMA_URL + "/api/tags", timeout=1.0)
            if r.status_code == 200:
                return "ollama"
        except Exception:
            pass
        if ANTHROPIC_KEY:
            # 2026-05-30 (fix Villa V9.4): so retornar "anthropic" se o pacote
            # estiver realmente importavel. Antes, com a chave no .env mas o
            # pacote ausente/meio-instalado, TODO stage caia em
            # ModuleNotFoundError -- o circuit breaker do Villa mitigava o custo,
            # mas o backend era detectado erroneamente e a saida virava mock
            # silencioso. Verificar a importabilidade torna a deteccao honesta
            # e permite cair direto para "mock" (log claro) sem desperdicar a
            # 1a tentativa de cada stage.
            import importlib.util as _ilu
            if _ilu.find_spec("anthropic") is not None:
                return "anthropic"
            log.warning(
                "ANTHROPIC_API_KEY presente mas pacote 'anthropic' nao "
                "importavel (pip install anthropic). Backend -> mock."
            )
        log.warning("Nenhum backend LLM disponivel! Respostas serao mock.")
        return "mock"

    def chat(self, prompt, system=None, model=None, temperature=0.3,
             max_tokens=2048, tier=None):
        """
        Envia prompt e retorna resposta em texto.
        """
        if system is None:
            system = DEFAULT_SYSTEM

        # Roteamento por tier (Policy Engine)
        # Atualizado 2026-05-07 -- Claude 4.5/4.6 (configuravel via .env).
        if tier and tier.startswith("claude_"):
            claude_models = {
                "claude_haiku":  get_env("LILO_CLAUDE_HAIKU",  "claude-haiku-4-5"),
                "claude_sonnet": get_env("LILO_CLAUDE_SONNET", "claude-sonnet-4-5"),
                "claude_opus":   get_env("LILO_CLAUDE_OPUS",   "claude-opus-4-5"),
            }
            claude_model = claude_models.get(tier, claude_models["claude_sonnet"])
            log.info("Tier %s -> Anthropic API (%s)", tier, claude_model)
            return self._chat_anthropic(prompt, system, temperature, max_tokens, model=claude_model)

        if tier and tier.startswith("ollama"):
            model = model or DEFAULT_MODEL
            log.info("Tier %s -> Ollama (%s)", tier, model)
            return self._chat_ollama(prompt, system, model, temperature, max_tokens)

        model = model or DEFAULT_MODEL

        if self.backend == "litellm":
            return self._chat_litellm(prompt, system, model, temperature, max_tokens)
        elif self.backend == "ollama":
            return self._chat_ollama(prompt, system, model, temperature, max_tokens)
        elif self.backend == "anthropic":
            return self._chat_anthropic(prompt, system, temperature, max_tokens)
        else:
            return "[MOCK] Backend indisponivel. Prompt recebido: " + prompt[:100]

    def list_models(self):
        """Lista modelos disponiveis no backend ativo."""
        try:
            if self.backend == "litellm":
                r = requests.get(LITELLM_URL + "/models", timeout=5)
                return [m["id"] for m in r.json().get("data", [])]
            elif self.backend == "ollama":
                r = requests.get(OLLAMA_URL + "/api/tags", timeout=5)
                return [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            log.error("Erro ao listar modelos: %s", e)
        return []

    def health(self):
        """Retorna status do cliente."""
        return {
            "backend": self.backend,
            "litellm_url": LITELLM_URL,
            "ollama_url": OLLAMA_URL,
            "default_model": DEFAULT_MODEL,
            "anthropic_configured": bool(ANTHROPIC_KEY),
        }

    def _chat_litellm(self, prompt, system, model, temperature, max_tokens):
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        api_key = get_env("LITELLM_API_KEY", "sk-litellm-local-dev")
        headers = {"Authorization": "Bearer " + api_key}
        r = requests.post(LITELLM_URL + "/chat/completions",
                          json=payload, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _normalize_keep_alive(value):
        """Normaliza keep_alive para o formato aceito pelo Ollama.

        Ollama aceita numero (segundos; -1 = manter para sempre) ou duracao
        com unidade ("2h", "30m"). String numerica SEM unidade ("-1", "300")
        passou a causar 400 ('time: missing unit in duration') em versoes
        recentes -- e e exatamente o que chega quando OLLAMA_KEEP_ALIVE=-1
        esta definido como variavel de ambiente do Windows (bench 2026-06-11,
        27/27 corridas com bug). Converte para int quando possivel.
        """
        v = str(value).strip()
        try:
            return int(v)
        except ValueError:
            return v

    def _chat_ollama(self, prompt, system, model, temperature, max_tokens):
        cot_suffix = (
            "\n\nIMPORTANT: Think step-by-step. First reason through the problem "
            "inside <thinking>...</thinking> tags, then provide your final answer. "
            "Local tokens are free -- be thorough in your reasoning."
        )
        enhanced_system = system + cot_suffix

        payload = {
            "model": model,
            "messages": [
                {"role": "system",    "content": enhanced_system},
                {"role": "user",      "content": prompt},
            ],
            "stream": False,
            "keep_alive": self._normalize_keep_alive(
                get_env("OLLAMA_KEEP_ALIVE", "2h")),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_gpu": 99,
                "num_thread": 8,
            },
        }
        r = requests.post(OLLAMA_URL + "/api/chat", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        response = r.json()["message"]["content"]

        if "</thinking>" in response:
            parts = response.split("</thinking>", 1)
            final = parts[1].strip() if len(parts) > 1 else response
            thinking = parts[0].replace("<thinking>", "").strip()
            if thinking:
                log.debug("CoT reasoning (%d chars): %s...", len(thinking), thinking[:200])
            return final if final else response
        return response

    def _chat_anthropic(self, prompt, system, temperature, max_tokens, model=None):
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        # Default atualizado 2026-05-07 (Claude 4.5/4.6); override via LILO_CLAUDE_SONNET.
        model = model or get_env("LILO_CLAUDE_SONNET", "claude-sonnet-4-5")
        log.info("Anthropic API -> %s", model)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return msg.content[0].text


# -- Singleton -----------------------------------------------------------------
_client_instance: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """Retorna instancia singleton do LLMClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
