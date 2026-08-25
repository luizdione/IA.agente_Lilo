"""Cliente Ollama do LILO v13 — /api/chat multi-turno com tools NATIVAS.

O que o legado nunca teve: array messages[] de verdade (system/user/assistant/
tool) e o parametro `tools` do Ollama. Herdado do legado (v12.15-legado):
classificacao de retry (_is_retryable), backoff exponencial, normalizacao do
keep_alive (evita 400 "missing unit in duration") e parse defensivo com
fallback para message.thinking (modelos raciocinantes).

`transport` e injetavel: os testes passam um FakeOllama e a suite roda
hermetica, sem rede. num_ctx e SEMPRE enviado (o default silencioso do
servidor, 2-4k, truncaria o historico do loop sem aviso).
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable

import requests

from lilo import config
from lilo.log import get_logger

log = get_logger("cliente")

Transport = Callable[[str, dict], dict]


def _normalize_keep_alive(valor: str):
    """"2h"/"30m" passam; string numerica ("-1", "0") vira int — o Ollama
    devolve 400 "time: missing unit in duration" p/ numero entre aspas."""
    v = str(valor).strip()
    try:
        return int(v)
    except ValueError:
        return v


def _is_retryable(exc: Exception) -> bool:
    """Timeout/conexao e HTTP 429/5xx re-tentam; outros 4xx falham rapido."""
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def _transport_requests(url: str, payload: dict) -> dict:
    r = requests.post(url, json=payload, timeout=config.timeout_s())
    r.raise_for_status()
    return r.json()


def _strip_thinking(texto: str) -> str:
    """Remove um bloco <thinking>...</thinking> no inicio da resposta."""
    t = texto.lstrip()
    if t.startswith("<thinking>"):
        fim = t.find("</thinking>")
        if fim != -1:
            return t[fim + len("</thinking>"):].lstrip()
    return texto


def _normalizar_tool_calls(brutos: list) -> list[dict]:
    """[{function:{name, arguments}}] -> [{name, arguments:dict}].

    `arguments` chega como dict na API nativa, mas ha combinacoes modelo/
    versao que devolvem string JSON — parse defensivo; ilegivel vira {} (o
    executor devolve [ERRO] e o modelo re-tenta)."""
    saida = []
    for tc in brutos or []:
        fn = tc.get("function") or {}
        nome = fn.get("name") or ""
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                log.warning("tool_call %s: arguments ilegivel", nome)
                args = {}
        if not isinstance(args, dict):
            args = {}
        if nome:
            saida.append({"name": nome, "arguments": args})
    return saida


class ClienteOllama:
    """Cliente minimo e sincrono do /api/chat (stream desligado no v13.0)."""

    def __init__(self, transport: Transport | None = None):
        self._transport = transport or _transport_requests

    def ping(self) -> bool:
        try:
            r = requests.get(config.ollama_host() + "/api/tags", timeout=2.0)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             model: str | None = None) -> dict[str, Any]:
        """Uma rodada de chat. Retorna:
        {"message": <mensagem crua p/ anexar ao historico>,
         "content": str, "tool_calls": [{name, arguments}], "done_reason": str}
        """
        payload: dict[str, Any] = {
            "model": model or config.modelo(),
            "messages": messages,
            "stream": False,
            "keep_alive": _normalize_keep_alive(config.keep_alive()),
            "options": {
                "num_ctx": config.num_ctx(),
                "temperature": config.temperatura(),
                "num_predict": config.max_tokens(),
            },
        }
        if tools:
            payload["tools"] = tools
        if not config.pensar():
            payload["think"] = False  # modelos sem thinking ignoram (200 OK)

        url = config.ollama_host() + "/api/chat"
        ultima: Exception | None = None
        for tentativa in range(config.retries() + 1):
            try:
                data = self._transport(url, payload)
                break
            except Exception as exc:  # noqa: BLE001 — classificado abaixo
                ultima = exc
                if tentativa < config.retries() and _is_retryable(exc):
                    espera = config.backoff_base() * (2 ** tentativa)
                    log.warning("chat: erro transitorio (%s) — retry %d/%d em %.1fs",
                                type(exc).__name__, tentativa + 1,
                                config.retries(), espera)
                    time.sleep(espera)
                    continue
                raise
        else:  # pragma: no cover — o loop retorna ou levanta
            raise ultima  # type: ignore[misc]

        msg = data.get("message") or {}
        tool_calls = _normalizar_tool_calls(msg.get("tool_calls") or [])
        content = msg.get("content") or ""
        if not content and not tool_calls:
            # Modelos raciocinantes as vezes poem tudo em .thinking
            content = msg.get("thinking") or ""
        content = _strip_thinking(content)

        done = data.get("done_reason") or ""
        if done == "length":
            log.warning("resposta truncada (num_predict=%d atingido)",
                        config.max_tokens())
        return {"message": msg, "content": content,
                "tool_calls": tool_calls, "done_reason": done}
