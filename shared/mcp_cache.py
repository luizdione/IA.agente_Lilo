"""
shared/mcp_cache.py -- Cache TTL de saidas de tools idempotentes (P1, V14.6)
============================================================================
Objetivo: melhorar TEMPO DE RESPOSTA e reduzir TOKENS/chamadas externas
repetidas. Tools idempotentes e caras (`lilo_scholar`, `lilo_web_search`,
`lilo_web_fetch`, `prism_classify`) costumam ser chamadas com os MESMOS
argumentos varias vezes na mesma sessao (o Claude reconsulta a mesma busca).

Reaproveita o `kv_memory` existente (SQLite local, TTL nativo com expiracao na
leitura) -- ns=`tool_cache`. Zero infraestrutura nova.

Principios:
  - So cacheia tools explicitamente marcadas como idempotentes (allow-list).
  - NUNCA cacheia erros (saidas que parecem falha) nem saidas vazias -- evita
    "gravar" uma falha transitoria de rede.
  - Chave = hash estavel de (tool, args, kwargs). Colisao improvavel (sha1).
  - Falha no cache nunca quebra a tool: cai para a chamada direta.
  - Marcador discreto de 1 linha no hit, para o Claude saber que o dado pode
    ter ate `idade` segundos (transparencia de frescor).

Env:
  LILO_MCP_CACHE_TTL   segundos de validade (default 600 = 10 min).
                       0 ou negativo desliga o cache (sempre chama direto).
"""

from __future__ import annotations

import hashlib
import json
import os
import time

DEFAULT_TTL = 600
CACHE_NS = "tool_cache"

# Marcadores que indicam falha -- nao devem ser cacheados.
_ERROR_PREFIXES = (
    "[erro", "[lilo] erro", "[lilo mcp]", "error:", "erro:", "traceback",
)
_ERROR_SUBSTRINGS = (
    "dial tcp", "recusou ativamente", "connection refused", "timed out",
    "timeout", "could not connect", "nao foi possivel", "não foi possível",
)


def get_ttl() -> int:
    raw = os.environ.get("LILO_MCP_CACHE_TTL")
    if raw is None or raw == "":
        return DEFAULT_TTL
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return DEFAULT_TTL


def make_key(tool_name: str, args: tuple, kwargs: dict) -> str:
    """Hash estavel de (tool, args, kwargs)."""
    try:
        canon = json.dumps(
            {"a": list(args), "k": kwargs},
            sort_keys=True, ensure_ascii=False, default=str,
        )
    except Exception:
        canon = repr((args, sorted(kwargs.items())))
    digest = hashlib.sha1(canon.encode("utf-8", "replace")).hexdigest()[:20]
    return f"{tool_name}:{digest}"


def _looks_like_error(out: str) -> bool:
    if not out or not out.strip():
        return True
    low = out.lstrip().lower()
    if low.startswith(_ERROR_PREFIXES):
        return True
    head = low[:400]
    return any(s in head for s in _ERROR_SUBSTRINGS)


def cached_call(tool_name: str, fn, args: tuple, kwargs: dict):
    """Executa `fn(*args, **kwargs)` com cache TTL via kv_memory.

    - TTL<=0 -> chama direto (cache off).
    - Hit valido -> devolve o valor cacheado com um marcador de 1 linha.
    - Miss / erro / saida nao-string -> chama, e cacheia so se for string "boa".
    Qualquer falha no cache cai para a chamada direta.
    """
    ttl = get_ttl()
    if ttl <= 0:
        return fn(*args, **kwargs)

    try:
        from shared.kv_memory import get_memory
        mem = get_memory()
        key = make_key(tool_name, args, kwargs)
    except Exception:
        return fn(*args, **kwargs)

    # Tentativa de leitura
    try:
        hit = mem.get(key, ns=CACHE_NS, default=None)
        if isinstance(hit, dict) and "out" in hit and "ts" in hit:
            age = max(0, int(time.time() - float(hit["ts"])))
            marker = f"[LILO cache · {age}s atras · dado pode estar desatualizado]\n"
            return marker + str(hit["out"])
    except Exception:
        pass  # leitura falhou -> segue para chamada direta

    # Miss -> chama de fato
    out = fn(*args, **kwargs)

    # Cacheia somente strings "boas"
    try:
        if isinstance(out, str) and not _looks_like_error(out):
            mem.set(
                key,
                {"out": out, "ts": time.time(), "tool": tool_name},
                ns=CACHE_NS,
                tags=f"cache,{tool_name}",
                ttl_seconds=ttl,
            )
    except Exception:
        pass  # gravar no cache nunca pode quebrar a tool

    return out
