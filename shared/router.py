r"""
shared/router.py -- Roteador ÚNICO do LILO (fonte-de-verdade do "qual agente")
=============================================================================
Condensa as TRÊS cascatas de roteamento que existiam duplicadas (o keyword-map
de lilo.py, o _detect_domain/_route_via_capabilities do villa e as keywords de
domínio da policy) numa só porta: `route_query()`.

Fonte-de-verdade dos domínios = o manifesto `capabilities()` que CADA subagente
já expõe (shared/base_agent.py): {name, description, keywords, cost_tier, ...}.
Nada de listas de keyword paralelas mantidas à mão.

Dois modos, selecionáveis por env `LILO_ROUTER`:
  - "embed"   -> similaridade semântica (cosine) da query contra a assinatura
                 de cada agente, reusando o stack de embeddings do scholaragent
                 (paraphrase-multilingual-MiniLM-L12-v2, local/CPU/offline).
  - "keyword" -> pontuação por fronteira de palavra sobre `capabilities().keywords`
                 (reproduz fielmente o antigo `_route_via_capabilities`).

Default = "keyword" (retrocompatível). O flip para "embed" é feito após validação
por golden-set. Se o embed falhar/indisponível, cai automaticamente no keyword.

IMPORTANTE: este módulo NÃO decide o MODELO (isso é da policy.py) nem o override
`\lilo opus` (modelo). Decide apenas QUAL agente/porta atende a query.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from .logger import get_logger

log = get_logger("Router")

# Agentes que NÃO são especialistas de domínio no matching semântico:
#   - villa   = o próprio orquestrador/pipeline (destino de tarefa ambígua/profunda)
#   - gateway = chat raso (destino de fallback quando nada casa)
# São excluídos da matriz de embeddings para não "sequestrar" o argmax.
_NON_SPECIALIST = frozenset({"villa", "gateway"})

# V13.3 (2026-08-17): recalibrado para o bge-m3 (embedder atual via Ollama).
# O 0.30 era do MiniLM; no bge-m3 textos NAO relacionados ficam em ~0.30-0.37
# ("quanto e 2+2?" dava prism=0.35 -> pergunta trivial recebia o help do prism),
# enquanto queries de dominio real pontuam >=0.47. O corte 0.45 separa os dois
# regimes (medido em scratchpad/calibra_router.py, 10 queries, 2026-08-17).
DEFAULT_THRESHOLD = 0.45


@dataclass(frozen=True)
class RouteDecision:
    """Resultado do roteamento. `scores` = {agente: score} p/ observabilidade/UI."""
    target: str
    method: str  # "embed" | "keyword" | "unavailable" | "ambiguous"
    score: float = 0.0
    scores: dict = field(default_factory=dict)
    reason: str = ""


def agent_signature(cap: dict) -> str:
    """Texto de assinatura semântica de um agente, a partir do seu capabilities()."""
    parts = [
        cap.get("name", ""),
        cap.get("description", ""),
        " ".join(cap.get("keywords", []) or []),
    ]
    return " ".join(p for p in parts if p).strip()


def _threshold() -> float:
    try:
        return float(os.getenv("LILO_ROUTER_THRESHOLD", str(DEFAULT_THRESHOLD)))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


# ── Rota por KEYWORD (replica _route_via_capabilities do villa) ──────────────

def _keyword_route(query: str, agents: dict[str, dict]) -> tuple[str | None, dict]:
    """Pontua cada agente por match de fronteira de palavra das suas keywords.
    Ignora 'villa' (pipeline). Retorna (argmax>0 | None, scores). NÃO aplica o
    filtro de disponibilidade -- isso é decidido em route_query (como no antigo
    route_target: detecta domínio, depois checa availability)."""
    ql = (query or "").lower()
    scores: dict[str, int] = {}
    best_name, best_score = None, 0
    for name, cap in agents.items():
        if name == "villa":
            continue
        score = 0
        for kw in (cap.get("keywords", []) or []):
            if not kw:
                continue
            # Fronteira de palavra (V10.6): evita 'cat' casar dentro de "catálise".
            if re.search(r"\b" + re.escape(str(kw).lower()) + r"\b", ql):
                score += 1
        scores[name] = score
        if score > best_score:
            best_name, best_score = name, score
    return (best_name if best_score > 0 else None), scores


# ── Rota por EMBEDDINGS (reusa scholaragent/brain, tudo lazy) ────────────────

@lru_cache(maxsize=1)
def get_embedder():
    """Singleton do Embedder local (sentence-transformers). Import lazy: só toca
    o modelo quando o modo embed é realmente usado."""
    from scholaragent.brain.embedder import Embedder
    return Embedder()


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# V13.3: cache em DISCO dos vetores de assinatura. Embedar as ~8 assinaturas
# custava ~12s de boot em CADA processo (CLI e 1º load do dashboard), refazendo
# um trabalho que só muda quando uma assinatura/modelo muda. Chave = modelo de
# embedding + sha1 da assinatura -> invalida sozinho no que mudar.
_SIG_CACHE_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "LILO", "router_sig_cache.json")


def _sig_cache_load() -> dict:
    try:
        import json
        with open(_SIG_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _sig_cache_save(cache: dict) -> None:
    try:
        import json
        os.makedirs(os.path.dirname(_SIG_CACHE_PATH), exist_ok=True)
        tmp = _SIG_CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, _SIG_CACHE_PATH)
    except Exception as e:  # cache é só aceleração; nunca derruba o roteador
        log.debug("router: falha ao salvar cache de assinaturas (%s)", e)


def _sig_key(model_id: str, signature: str) -> str:
    import hashlib
    return model_id + ":" + hashlib.sha1(signature.encode("utf-8")).hexdigest()


class _EmbedRouter:
    """Embeda a assinatura de cada especialista uma vez; roteia por cosine."""

    def __init__(self, agents: dict[str, dict]):
        emb = get_embedder()
        model_id = str(getattr(emb, "_ollama_model", None) or
                       getattr(emb, "model_name", "") or "st")
        self.names = [n for n in agents if n not in _NON_SPECIALIST]
        cache = _sig_cache_load()
        dirty = False
        self.vecs = {}
        for n in self.names:
            sig = agent_signature(agents[n])
            key = _sig_key(model_id, sig)
            vec = cache.get(key)
            if vec is None:
                vec = list(emb.embed_query(sig))
                cache[key] = vec
                dirty = True
            self.vecs[n] = vec
        if dirty:
            _sig_cache_save(cache)

    def route(self, query: str, threshold: float) -> tuple[str | None, dict]:
        if not self.names:
            return None, {}
        q = get_embedder().embed_query(query)
        scores = {n: _cosine(q, v) for n, v in self.vecs.items()}
        best = max(scores, key=scores.get)
        return (best if scores[best] >= threshold else None), scores


# Cache do _EmbedRouter, invalidado quando o conjunto/assinatura de agentes muda.
_EMBED_CACHE: dict[tuple, _EmbedRouter] = {}


def _get_embed_router(agents: dict[str, dict]) -> _EmbedRouter:
    key = tuple(sorted(
        (n, agent_signature(c)) for n, c in agents.items() if n not in _NON_SPECIALIST
    ))
    r = _EMBED_CACHE.get(key)
    if r is None:
        r = _EmbedRouter(agents)
        _EMBED_CACHE.clear()   # mantém só a geração corrente
        _EMBED_CACHE[key] = r
    return r


# ── Porta única ──────────────────────────────────────────────────────────────

def route_query(
    query: str,
    agents: dict[str, dict],
    *,
    available: set[str] | None = None,
) -> RouteDecision:
    """Decide QUAL agente atende a query.

    Args:
        query     -- texto do usuário.
        agents    -- {nome: capabilities()} de cada agente carregado.
        available -- conjunto de agentes carregados/disponíveis (opcional). Se um
                     domínio for detectado mas não estiver disponível, roteia para
                     "villa" (pipeline), como no route_target legado.

    Returns:
        RouteDecision(target, method, score, scores, reason).
    """
    mode = (os.getenv("LILO_ROUTER", "keyword") or "keyword").strip().lower()

    # 1) Embeddings (se ligado). Falha/indisponível -> cai no keyword.
    if mode == "embed":
        try:
            target, scores = _get_embed_router(agents).route(query, _threshold())
            if target and (available is None or target in available):
                return RouteDecision(target, "embed", float(scores.get(target, 0.0)),
                                     scores, "cosine >= threshold")
            if target and available is not None and target not in available:
                return RouteDecision("villa", "unavailable", 0.0, scores,
                                     "domínio '%s' indisponível -> pipeline" % target)
            # abaixo do threshold -> segue para o fallback keyword/gateway
        except Exception as e:  # noqa: BLE001 -- qualquer falha do embed é degradável
            log.warning("router embed indisponível (%s); fallback keyword", e)

    # 2) Keyword (default e fallback).
    target, scores = _keyword_route(query, agents)
    if target and (available is None or target in available):
        return RouteDecision(target, "keyword", float(scores.get(target, 0)),
                             scores, "keyword match")
    if target and available is not None and target not in available:
        return RouteDecision("villa", "unavailable", 0.0, scores,
                             "domínio '%s' indisponível -> pipeline" % target)

    # 3) Nada casou -> gateway (chat raso). O caller (villa wrapper) pode
    #    reescrever para "villa" quando a query for profunda (_is_deep_query).
    return RouteDecision("gateway", "ambiguous", 0.0, scores, "sem domínio claro")
