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
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .logger import get_logger
from .utils import PROJECT_ROOT

log = get_logger("CostTracker")

# 2026-05-20: caminho configuravel via env -- permite mover o SQLite
# volatil para fora de pastas sincronizadas (OneDrive) onde o SQLite
# pode lancar "disk I/O error"/locking. Default inalterado.
DB_PATH = Path(os.environ.get(
    "LILO_COST_DB", str(PROJECT_ROOT / "logs" / "cost_tracking.db")))

# 2026-05-31 (V10.2): fallback automatico para path gravavel.
# Quando o path primario e read-only / disco cheio / sandbox compartilhado,
# o codigo antigo soltava WARN "disk I/O error" a CADA log_request e ainda
# pagava o custo de abrir a conexao (latencia por stage, secao 3.2 do
# relat. 2026-05-30). Agora testamos a gravabilidade UMA vez no boot e, se
# falhar, degradamos para tempfile silenciosamente. Se nem o tempfile
# funcionar, a telemetria e desativada (no-op) em vez de spammar/atrasar.
_TEMP_DB = Path(tempfile.gettempdir()) / "lilo_cost_tracking.db"


def _resolve_writable_db(preferred: Path) -> tuple[Optional[Path], bool]:
    """Retorna (path_gravavel, degraded). path=None => telemetria off.

    Tenta o path preferido; se nao for gravavel, cai para tempfile. Se nem
    o tempfile servir, devolve (None, True) e o tracker vira no-op.
    """
    for candidate, is_fallback in ((preferred, False), (_TEMP_DB, True)):
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            # Teste real de escrita SQLite (mais fiel que os.access).
            with sqlite3.connect(str(candidate)) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS _probe (x INTEGER)")
            if is_fallback:
                log.warning(
                    "CostTracker: path primario nao-gravavel; usando fallback "
                    "tempfile %s (telemetria preservada, sem spam de I/O).",
                    candidate)
            return candidate, is_fallback
        except Exception as _e:
            log.debug("CostTracker: path %s indisponivel: %s", candidate, _e)
    log.warning("CostTracker: nenhum path gravavel; telemetria DESATIVADA "
                "nesta sessao (no-op, sem custo por stage).")
    return None, True


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
        preferred = db_path or DB_PATH
        # V10.2: resolve um path gravavel UMA vez; se nada servir, no-op.
        resolved, degraded = _resolve_writable_db(preferred)
        self.db_path = resolved
        self.enabled = resolved is not None
        self.degraded = degraded
        if self.enabled:
            self._init_db()

    def _init_db(self):
        try:
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
        except Exception as _e:
            log.warning("CostTracker._init_db falhou (telemetria nao-fatal; disco cheio/lock?): %s", _e)

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
        if not self.enabled:
            return  # V10.2: telemetria desativada -> no-op (sem latencia/spam)
        try:
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
        except Exception as _e:
            log.warning("CostTracker.log_request falhou (telemetria nao-fatal): %s", _e)

    def daily_summary(self, target_date: Optional[str] = None) -> dict:
        """Resumo de custos do dia."""
        d = target_date or date.today().isoformat()
        if not self.enabled:
            return {"date": d, "total_requests": 0, "total_cost_usd": 0.0,
                    "total_tokens_in": 0, "total_tokens_out": 0,
                    "by_backend": {}, "by_subagent": {}, "disabled": True}
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
        if not self.enabled:
            return []
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
