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

# V16 QW4: retry/backoff transitorio centralizado no chat().
# Tentativas EXTRAS apos a 1a (0 = comportamento antigo, sem retry).
LLM_RETRIES   = int(get_env("LILO_LLM_RETRIES",  "2"))
LLM_BACKOFF   = float(get_env("LILO_LLM_BACKOFF", "1.5"))  # base do backoff exp.


def _is_retryable(exc) -> bool:
    """True para erros transitorios (vale a pena re-tentar).

    - Timeout / ConnectionError de rede        -> retry
    - HTTP 429 (rate-limit) e 5xx (server)     -> retry
    - HTTP 4xx (exceto 429: request invalida)  -> fail-fast (nao re-tenta)
    Qualquer outra excecao -> nao re-tenta (deixa propagar/cair p/ fallback).
    """
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError):
        sc = getattr(getattr(exc, "response", None), "status_code", 0) or 0
        return sc == 429 or 500 <= sc < 600
    return False

# Matriz de modelos centralizada em shared/models.py. Re-exportada aqui para
# compatibilidade (villa_lobos, gateway, chat_memory fazem
# `from shared.llm_client import MODELS`). Trocar de modelo: .env ou
# shared/models.py — num só lugar.
from shared.models import MODELS, DEFAULT_MODEL  # noqa: E402,F401

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
             max_tokens=2048, tier=None, cot=True):
        """
        Envia prompt e retorna resposta em texto.

        cot: quando False, NAO injeta o chain-of-thought <thinking> no Ollama
        (resposta direta, ~2x mais rapida). Use em perguntas simples/chat;
        mantenha True nos estagios do pipeline onde o raciocinio agrega.
        """
        if system is None:
            # V15 FASE 0: honestidade no fallback (so quando o caller nao traz
            # system proprio). Respeita o kill-switch LILO_PROMPT_BLOCKS.
            from .prompt_blocks import compose_system
            system = compose_system(DEFAULT_SYSTEM, stage="output")

        # V16 QW4: retry/backoff em torno do dispatch. Erros transitorios
        # (timeout/conexao/429/5xx) sao re-tentados com backoff exponencial;
        # 4xx falham rapido. Centraliza p/ gateway/judge/paper, que chamavam
        # chat() sem o retry que o Villa ja faz manualmente.
        import time as _time
        last_exc = None
        for attempt in range(LLM_RETRIES + 1):
            try:
                return self._dispatch_chat(
                    prompt, system, model, temperature, max_tokens, tier, cot
                )
            except Exception as exc:  # noqa: BLE001 -- classifica abaixo
                last_exc = exc
                if attempt < LLM_RETRIES and _is_retryable(exc):
                    delay = LLM_BACKOFF * (2 ** attempt)
                    log.warning(
                        "chat: erro transitorio (%s) -- retry %d/%d em %.1fs",
                        type(exc).__name__, attempt + 1, LLM_RETRIES, delay,
                    )
                    _time.sleep(delay)
                    continue
                raise
        raise last_exc  # pragma: no cover (loop sempre retorna ou levanta)

    def _dispatch_chat(self, prompt, system, model, temperature,
                       max_tokens, tier, cot):
        """Despacho para o backend (sem retry). Veja chat()."""
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
            return self._chat_ollama(prompt, system, model, temperature, max_tokens, cot=cot)

        model = model or DEFAULT_MODEL

        if self.backend == "litellm":
            return self._chat_litellm(prompt, system, model, temperature, max_tokens)
        elif self.backend == "ollama":
            return self._chat_ollama(prompt, system, model, temperature, max_tokens, cot=cot)
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
        # Parse defensivo (ver _chat_ollama): choices[] vazio ou sem content
        # vira mensagem acionavel em vez de KeyError/IndexError cru.
        data = r.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LiteLLM retornou sem choices: %s" % str(data)[:200])
        content = (choices[0].get("message") or {}).get("content")
        if not content:
            raise ValueError("LiteLLM choice sem content: %s" % str(data)[:200])
        return content

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

    def _chat_ollama(self, prompt, system, model, temperature, max_tokens, cot=True):
        # V15 FASE 2: raciocinio minucioso DENTRO de <thinking> (tokens locais
        # baratos -> qualidade), mas a RESPOSTA FINAL no comprimento que a
        # pergunta exige. V15.1: cot=False (ex.: gateway/chat) PULA o <thinking>
        # -> resposta direta, ~2x mais rapida em perguntas simples.
        if cot:
            cot_suffix = (
                "\n\nIMPORTANTE: raciocine passo-a-passo DENTRO de "
                "<thinking>...</thinking> (seja minucioso aqui; tokens locais sao "
                "baratos). Depois de </thinking>, escreva a RESPOSTA FINAL ao "
                "usuario de forma direta, no comprimento que a pergunta exige, sem "
                "repetir o raciocinio."
            )
        else:
            cot_suffix = (
                "\n\nResponda de forma DIRETA e objetiva, sem mostrar raciocinio "
                "intermediario nem usar tags <thinking>."
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
        # Parse defensivo: raise_for_status() so valida o STATUS HTTP, nao o
        # corpo. Um 200 com payload inesperado (truncagem, erro embutido,
        # modelo descarregado) faria r.json()["message"]["content"] estourar
        # KeyError/TypeError cru -- mascarado como falha generica do stage e
        # disparando fallback inutil. Mensagem acionavel em vez de KeyError.
        data = r.json()
        _msg = data.get("message") or {}
        response = _msg.get("content")
        if not response:
            # V14.4: modelos de RACIOCINIO (ex.: gpt-oss) colocam o texto no
            # campo 'thinking' e deixam 'content' VAZIO quando o num_predict
            # acaba no raciocinio. Usar o thinking como fallback evita perder a
            # resposta (o JSON/conteudo costuma vir no fim do thinking). Ver
            # bench 2026-06-13 (juiz cloud com 400 tokens -> 11/18 vazios).
            response = _msg.get("thinking") or ""
        if not response:
            raise ValueError(
                "Ollama retornou payload sem message.content (modelo=%s): %s"
                % (model, str(data)[:200]))

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

        # Prompt caching (2026-06-13): marca o bloco `system` como cacheavel
        # (cache_control ephemeral). E ADITIVO e seguro -- a API ignora o cache
        # quando o bloco fica abaixo do minimo de tokens, sem erro nem custo.
        # O ganho real (ate ~90% no prefixo) aparece quando o MESMO system
        # grande e reenviado em <5min, como nos varios stages do Villa Lobos
        # que compartilham instrucoes. Desligue com LILO_ANTHROPIC_CACHE=0.
        use_cache = get_env("LILO_ANTHROPIC_CACHE", "1") not in ("0", "false", "False", "")
        common = dict(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        try:
            if use_cache:
                msg = client.messages.create(system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }], **common)
            else:
                msg = client.messages.create(system=system, **common)
        except TypeError:
            # SDK antigo sem suporte a `system` em blocos -> string simples.
            msg = client.messages.create(system=system, **common)
        return msg.content[0].text


# -- Singleton -----------------------------------------------------------------
_client_instance: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """Retorna instancia singleton do LLMClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
