"""
shared/metrics.py -- Telemetria leve de economia do MCP (V14.7)
===============================================================
Instrumenta as otimizacoes V14.5 (guarda de orcamento) e V14.6 (cache TTL)
para que o dashboard exiba **quanto o LILO economiza** ao Claude:
  - hits/misses do cache de tools idempotentes (hit-rate);
  - truncamentos da guarda + caracteres/tokens poupados.

Persistido no `kv_memory` existente (ns=`mcp_metrics`), em buckets diarios
(uma linha por dia, key=YYYY-MM-DD). RMW protegido por lock in-process; toda
gravacao e best-effort e NUNCA pode quebrar uma tool.

Como a estimativa de tokens e aproximada: ~4 chars/token (heuristica padrao
para texto latino). Exibida como "tokens (aprox.)".

Env:
  LILO_MCP_METRICS   '0' desliga a coleta (default ligado).
"""

from __future__ import annotations

import os
import threading
from datetime import date, timedelta

METRICS_NS = "mcp_metrics"
CHARS_PER_TOKEN = 4
_LOCK = threading.Lock()


def _enabled() -> bool:
    return os.environ.get("LILO_MCP_METRICS", "1") not in ("0", "false", "False", "")


def _today_key() -> str:
    return date.today().isoformat()


def _empty_day() -> dict:
    return {
        "cache": {"hits": 0, "misses": 0, "by_tool": {}},
        "budget": {"truncations": 0, "chars_saved": 0, "by_tool": {}},
    }


def _merge_tool(bucket: dict, tool: str, **deltas) -> None:
    t = bucket["by_tool"].setdefault(tool, {})
    for k, v in deltas.items():
        t[k] = t.get(k, 0) + v


def _record(mut) -> None:
    """Aplica `mut(day_dict)` no bucket de hoje, com RMW protegido."""
    if not _enabled():
        return
    try:
        from shared.kv_memory import get_memory
        mem = get_memory()
        key = _today_key()
        with _LOCK:
            day = mem.get(key, ns=METRICS_NS, default=None)
            if not isinstance(day, dict):
                day = _empty_day()
            day.setdefault("cache", _empty_day()["cache"])
            day.setdefault("budget", _empty_day()["budget"])
            mut(day)
            mem.set(key, day, ns=METRICS_NS, tags="metrics")
    except Exception:
        pass  # telemetria nunca derruba a tool


def record_cache(tool: str, hit: bool) -> None:
    def mut(day):
        c = day["cache"]
        if hit:
            c["hits"] += 1
            _merge_tool(c, tool, hits=1)
        else:
            c["misses"] += 1
            _merge_tool(c, tool, misses=1)
    _record(mut)


def record_budget(tool: str, chars_saved: int) -> None:
    if chars_saved <= 0:
        return

    def mut(day):
        b = day["budget"]
        b["truncations"] += 1
        b["chars_saved"] += int(chars_saved)
        _merge_tool(b, tool, truncations=1, chars_saved=int(chars_saved))
    _record(mut)


# -- Leitura / agregacao (consumida pelo dashboard) --------------------------

def get_day(day_key: str | None = None) -> dict:
    """Bucket de um dia (default hoje). Sempre devolve a estrutura completa."""
    base = _empty_day()
    try:
        from shared.kv_memory import get_memory
        mem = get_memory()
        d = mem.get(day_key or _today_key(), ns=METRICS_NS, default=None)
        if isinstance(d, dict):
            base["cache"].update(d.get("cache", {}))
            base["budget"].update(d.get("budget", {}))
    except Exception:
        pass
    return base


def summary(days: int = 7) -> dict:
    """Agrega os ultimos `days` dias (inclui hoje). Calcula hit-rate e tokens."""
    keys = [(date.today() - timedelta(days=i)).isoformat() for i in range(days)]
    hits = misses = trunc = chars = 0
    by_tool: dict[str, dict] = {}
    for k in keys:
        d = get_day(k)
        c, b = d["cache"], d["budget"]
        hits += c.get("hits", 0)
        misses += c.get("misses", 0)
        trunc += b.get("truncations", 0)
        chars += b.get("chars_saved", 0)
        for tool, tv in c.get("by_tool", {}).items():
            e = by_tool.setdefault(tool, {})
            e["hits"] = e.get("hits", 0) + tv.get("hits", 0)
            e["misses"] = e.get("misses", 0) + tv.get("misses", 0)
        for tool, tv in b.get("by_tool", {}).items():
            e = by_tool.setdefault(tool, {})
            e["truncations"] = e.get("truncations", 0) + tv.get("truncations", 0)
            e["chars_saved"] = e.get("chars_saved", 0) + tv.get("chars_saved", 0)
    total = hits + misses
    return {
        "days": days,
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_total": total,
        "hit_rate": (hits / total) if total else 0.0,
        "budget_truncations": trunc,
        "chars_saved": chars,
        "tokens_saved_approx": chars // CHARS_PER_TOKEN,
        "by_tool": by_tool,
    }
