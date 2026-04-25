"""
shared/cost_tracker.py — Rastreador de custos do LILO
=====================================================
Registra cada chamada LLM em SQLite local para monitoramento.

Uso:
    from shared.cost_tracker import get_tracker
    tracker = get_tracker()
    tracker.log_request("ollama", "llama3.1:8b", tokens_in=100, tokens_out=200, cost=0.0)
    summary = tracker.daily_summary()
"""

import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .logger import get_logger
from .utils import PROJECT_ROOT

log = get_logger("CostTracker")

DB_PATH = PROJECT_ROOT / "logs" / "cost_tracking.db"


@dataclass
class RequestLog:
    timestamp: str
    backend: str      # "ollama", "claude_sonnet", "claude_opus", "no_llm"
    model: str
    subagent: str     # "sql", "pdf", "scholar", "gateway"
    tokens_in: int
    tokens_out: int
    cost_usd: float
    query_preview: str  # primeiros 80 chars
    tier: str          # ExecutionTier value


class CostTracker:
    """Rastreia custos e uso de modelos em SQLite local."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    backend TEXT NOT NULL,
                    model TEXT,
                    subagent TEXT,
                    tier TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    query_preview TEXT,
                    duration_ms INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date ON requests(date)
            """)

    def log_request(
        self,
        backend: str,
        model: str,
        subagent: str = "",
        tier: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        query_preview: str = "",
        duration_ms: int = 0,
    ):
        """Registra uma chamada LLM."""
        now = datetime.now()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO requests
                   (timestamp, date, backend, model, subagent, tier, tokens_in, tokens_out, cost_usd, query_preview, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now.isoformat(),
                    now.strftime("%Y-%m-%d"),
                    backend,
                    model or "",
                    subagent,
                    tier,
                    tokens_in,
                    tokens_out,
                    cost_usd,
                    query_preview[:80],
                    duration_ms,
                ),
            )
        log.info(f"Logged: {backend}/{model} | ${cost_usd:.4f} | {tokens_in+tokens_out} tokens")

    def daily_summary(self, target_date: Optional[str] = None) -> dict:
        """Resumo de custos do dia."""
        d = target_date or date.today().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as total_requests,
                     COALESCE(SUM(cost_usd), 0) as total_cost,
                     COALESCE(SUM(tokens_in), 0) as total_tokens_in,
                     COALESCE(SUM(tokens_out), 0) as total_tokens_out
                   FROM requests WHERE date = ?""",
                (d,),
            ).fetchone()

            by_backend = conn.execute(
                """SELECT backend, COUNT(*), COALESCE(SUM(cost_usd), 0)
                   FROM requests WHERE date = ? GROUP BY backend""",
                (d,),
            ).fetchall()

            by_subagent = conn.execute(
                """SELECT subagent, COUNT(*), COALESCE(SUM(cost_usd), 0)
                   FROM requests WHERE date = ? GROUP BY subagent""",
                (d,),
            ).fetchall()

        return {
            "date": d,
            "total_requests": row[0],
            "total_cost_usd": round(row[1], 4),
            "total_tokens_in": row[2],
            "total_tokens_out": row[3],
            "by_backend": {r[0]: {"count": r[1], "cost": round(r[2], 4)} for r in by_backend},
            "by_subagent": {r[0]: {"count": r[1], "cost": round(r[2], 4)} for r in by_subagent},
        }

    def recent_requests(self, limit: int = 20) -> list[dict]:
        """Últimas N requests."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ── Singleton ────────────────────────────────────────────────────────────────
_tracker: Optional[CostTracker] = None


def get_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
