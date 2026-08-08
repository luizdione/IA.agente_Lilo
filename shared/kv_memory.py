"""
shared/kv_memory.py -- Memoria chave-valor persistente do LILO
==============================================================
Camada robusta sobre SQLite para o agente lembrar fatos entre sessoes
(preferencias, decisoes, anotacoes do usuario).

Diferente de chat_memory.py (historico de mensagens), aqui sao pares
key/value categorizados por namespace, com timestamps, tags, TTL e
busca textual.

v10.3 (2026-05-07):
- DB padrao em %LOCALAPPDATA%/LILO (Windows) ou ~/.local/share/lilo,
  fora do OneDrive -- evita "disk I/O error" e locks de sync.
- Override via env LILO_KV_MEMORY_DB.
- Migracao automatica de memory/kv_memory.db (legado, no OneDrive).
- TTL/expires_at opcional + cleanup automatico.
- Full-text search (LIKE) em key/value/tags.
- WAL mode + busy_timeout 5s.
- Export/import JSON para backup.

Uso:
    from shared.kv_memory import get_memory
    mem = get_memory()
    mem.set("preferred_model", "claude-sonnet-4-5", ns="user")
    mem.set("scratch", "tmp data", ns="cache", ttl_seconds=3600)
    val = mem.get("preferred_model", ns="user")
    mem.search("claude")               # busca textual
    mem.list(ns="user")
    mem.export_json(ns="user")          # backup
    mem.delete("preferred_model", ns="user")
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .logger import get_logger
from .utils import PROJECT_ROOT, get_env

log = get_logger("KVMemory")

# Schema atual. Bump quando adicionar/remover colunas.
SCHEMA_VERSION = 3  # v3 (V18.3 E2): coluna kv.embedding BLOB

# V18.3 (E2, ROADMAP item D): embeddings semanticos opcionais, computados no
# set() via Ollama /api/embed com o modelo de OLLAMA_MODEL_EMBED (mxbai ja e
# o default do .env). Falha/offline NUNCA quebra a escrita: a linha fica sem
# embedding e a busca semantica degrada para LIKE. Sem ChromaDB aqui de
# proposito -- SQLite+numpy basta na escala de memoria pessoal (Chroma fica
# no scholaragent). Desligue com LILO_KV_EMBED=0.
EMBED_ENABLED = str(get_env("LILO_KV_EMBED", "1")).strip().lower() not in (
    "0", "false", "off")
EMBED_TIMEOUT = float(get_env("LILO_KV_EMBED_TIMEOUT", "4.0"))


def _ollama_embed(text: str) -> Optional[list]:
    """Vetor de embedding via Ollama /api/embed; None quando indisponivel."""
    try:
        import requests
        from .llm_client import MODELS, OLLAMA_URL
        r = requests.post(
            OLLAMA_URL + "/api/embed",
            json={"model": MODELS["embed"], "input": str(text)[:2000]},
            timeout=EMBED_TIMEOUT)
        r.raise_for_status()
        embs = r.json().get("embeddings") or []
        return embs[0] if embs else None
    except Exception as e:
        log.debug("embed indisponivel: %s", e)
        return None


def _default_db_path() -> Path:
    """Caminho padrao do banco SQLite, fora do OneDrive.

    Windows:  %LOCALAPPDATA%\\LILO\\memory\\kv_memory.db
    Unix:     ~/.local/share/lilo/memory/kv_memory.db
    Override: env LILO_KV_MEMORY_DB (caminho absoluto).
    """
    env_path = get_env("LILO_KV_MEMORY_DB", "")
    if env_path:
        return Path(env_path).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", "")) or Path.home() / "AppData" / "Local"
        return base / "LILO" / "memory" / "kv_memory.db"
    return Path.home() / ".local" / "share" / "lilo" / "memory" / "kv_memory.db"


# Caminho legado (no OneDrive) -- migracao automatica no _init_db.
LEGACY_DB_PATH = PROJECT_ROOT / "memory" / "kv_memory.db"
DB_PATH = _default_db_path()


class KVMemory:
    """Key-Value store SQLite com namespaces, tags, TTL e busca textual."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # V18.3 E2: embedder injetavel (testes/offline). None = _ollama_embed
        # quando LILO_KV_EMBED=1; callable text -> list[float] | None.
        self.embedder = None
        self._maybe_migrate_legacy()
        self._init_db()

    # ---- migracao do banco antigo (no OneDrive) ----------------------------

    def _maybe_migrate_legacy(self) -> None:
        """Se existir kv_memory.db legado no OneDrive e o novo ainda nao,
        copia uma vez para o local fora-OneDrive. Nao remove o original
        (usuario decide quando excluir)."""
        try:
            if (LEGACY_DB_PATH.exists()
                    and LEGACY_DB_PATH != self.db_path
                    and not self.db_path.exists()):
                import shutil as _sh
                _sh.copyfile(str(LEGACY_DB_PATH), str(self.db_path))
                log.info(
                    "Migrado kv_memory.db do OneDrive -> %s "
                    "(o original foi mantido como backup)",
                    self.db_path,
                )
        except Exception as e:
            log.warning("Falha na migracao do kv_memory legado: %s", e)

    # ---- schema + helpers ---------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Conexao com WAL + busy_timeout para mitigar locks."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error:
            pass
        return conn

    def _init_db(self) -> None:
        # Etapa 1: cria a tabela kv e meta. Ainda nao criamos os indices
        # de colunas potencialmente ausentes em bancos legados.
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    ns TEXT NOT NULL DEFAULT 'default',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    PRIMARY KEY (ns, key)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kv_ns ON kv(ns)")
            # tabela de metadados
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # registra schema_version se ausente
            cur = conn.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
            if cur is None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION)),
                )
            conn.commit()
        # Etapa 2: migracao incremental -- adiciona colunas faltantes
        # ANTES de criar indices que dependem delas (fix v10.4).
        self._ensure_column("expires_at", "TEXT")
        self._ensure_column("tags", "TEXT")
        self._ensure_column("embedding", "BLOB")  # V18.3 E2 (schema v3)
        # Etapa 3: agora e seguro criar indices das colunas migraveis.
        with self._connect() as conn:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kv_expires ON kv(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kv_tags ON kv(tags)")
            conn.commit()

    def _ensure_column(self, name: str, type_sql: str) -> None:
        with self._connect() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(kv)").fetchall()]
            if name not in cols:
                log.info("Adicionando coluna kv.%s (migracao)", name)
                conn.execute(f"ALTER TABLE kv ADD COLUMN {name} {type_sql}")
                conn.commit()

    # ---- CRUD ---------------------------------------------------------------

    def set(
        self,
        key: str,
        value: Any,
        ns: str = "default",
        tags: str = "",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Insere ou atualiza um valor.

        Args:
            key: chave dentro do namespace
            value: qualquer JSON-serializavel
            ns: namespace (default, user, project, cache...)
            tags: csv com tags
            ttl_seconds: se >0, expira apos esses segundos
        """
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, default=str)
        now = datetime.now()
        expires = (
            (now + timedelta(seconds=int(ttl_seconds))).isoformat()
            if ttl_seconds and ttl_seconds > 0 else None
        )
        # V18.3 E2: embedding computado na escrita (chave da signal ao vetor).
        # None (offline/desligado) sobrescreve embedding antigo de proposito:
        # o valor mudou, manter o vetor velho retornaria matches errados.
        emb = self._embed_blob(f"{key}: {value}")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO kv (ns, key, value, tags, created_at, updated_at, expires_at, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(ns, key) DO UPDATE SET
                     value=excluded.value,
                     tags=excluded.tags,
                     updated_at=excluded.updated_at,
                     expires_at=excluded.expires_at,
                     embedding=excluded.embedding""",
                (ns, key, value, tags, now.isoformat(), now.isoformat(),
                 expires, emb),
            )
            conn.commit()
        log.info("KV set %s/%s (%d chars%s)",
                 ns, key, len(value),
                 f", ttl={ttl_seconds}s" if ttl_seconds else "")

    def get(self, key: str, ns: str = "default", default: Any = None) -> Any:
        """Le um valor. Retorna default se ausente OU expirado."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM kv WHERE ns=? AND key=?",
                (ns, key),
            ).fetchone()
        if not row:
            return default
        val, expires_at = row
        if expires_at and datetime.now().isoformat() > expires_at:
            # entrada expirada -- limpa silenciosamente
            self.delete(key, ns=ns)
            return default
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    def delete(self, key: str, ns: str = "default") -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM kv WHERE ns=? AND key=?", (ns, key))
            conn.commit()
            return cur.rowcount > 0

    def list(
        self,
        ns: Optional[str] = None,
        tag: Optional[str] = None,
        include_expired: bool = False,
    ) -> list[dict]:
        sql = (
            "SELECT ns, key, value, tags, created_at, updated_at, expires_at FROM kv"
        )
        clauses: list[str] = []
        params: list[Any] = []
        if ns:
            clauses.append("ns=?")
            params.append(ns)
        if tag:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")
        if not include_expired:
            now = datetime.now().isoformat()
            clauses.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(now)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out = []
        for ns_, k, v, t, c, u, e in rows:
            try:
                v_parsed = json.loads(v)
            except Exception:
                v_parsed = v
            out.append({
                "ns": ns_, "key": k, "value": v_parsed, "tags": t,
                "created_at": c, "updated_at": u, "expires_at": e,
            })
        return out

    # ---- busca textual ------------------------------------------------------

    def search(
        self,
        query: str,
        ns: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Busca substring em key, value e tags (case-insensitive)."""
        q = f"%{query.lower()}%"
        sql = (
            "SELECT ns, key, value, tags, updated_at, expires_at FROM kv WHERE ("
            "LOWER(key) LIKE ? OR LOWER(value) LIKE ? OR LOWER(tags) LIKE ?)"
        )
        params: list[Any] = [q, q, q]
        if ns:
            sql += " AND ns=?"
            params.append(ns)
        # exclui expirados
        sql += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(datetime.now().isoformat())
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out = []
        for ns_, k, v, t, u, e in rows:
            try:
                v_parsed = json.loads(v)
            except Exception:
                v_parsed = v
            out.append({
                "ns": ns_, "key": k, "value": v_parsed, "tags": t,
                "updated_at": u, "expires_at": e,
            })
        return out

    # ---- busca semantica (V18.3 E2, ROADMAP item D) ------------------------

    def _embed_blob(self, text: str) -> Optional[bytes]:
        """bytes float32 do embedding do texto, ou None (offline/desligado)."""
        fn = self.embedder or (_ollama_embed if EMBED_ENABLED else None)
        if fn is None:
            return None
        try:
            vec = fn(text)
            if not vec:
                return None
            import numpy as np
            return np.asarray(vec, dtype=np.float32).tobytes()
        except Exception as e:
            log.debug("embed falhou: %s", e)
            return None

    def search_semantic(
        self,
        query: str,
        ns: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.25,
    ) -> list[dict]:
        """Busca por SIGNIFICADO (cosseno sobre embeddings locais).

        Fallback transparente: sem embedder/Ollama, ou sem nenhuma linha
        com embedding acima de min_score, degrada para search() textual —
        cada item sai com "match": "semantic" (+ "score") ou "like_fallback".
        """
        qb = self._embed_blob(query)
        if qb is None:
            out = self.search(query, ns=ns, limit=limit)
            for o in out:
                o["match"] = "like_fallback"
            return out
        import numpy as np
        qv = np.frombuffer(qb, dtype=np.float32)
        qn = qv / (np.linalg.norm(qv) or 1.0)
        sql = ("SELECT ns, key, value, tags, updated_at, embedding FROM kv "
               "WHERE embedding IS NOT NULL")
        params: list[Any] = []
        if ns:
            sql += " AND ns=?"
            params.append(ns)
        sql += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(datetime.now().isoformat())
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        scored: list[dict] = []
        for ns_, k, v, t, u, blob in rows:
            try:
                ev = np.frombuffer(blob, dtype=np.float32)
                if ev.shape != qv.shape:
                    continue  # dimensao diferente (troca de modelo de embed)
                score = float(np.dot(qn, ev / (np.linalg.norm(ev) or 1.0)))
            except Exception:
                continue
            if score < min_score:
                continue
            try:
                v_parsed = json.loads(v)
            except Exception:
                v_parsed = v
            scored.append({
                "ns": ns_, "key": k, "value": v_parsed, "tags": t,
                "updated_at": u, "score": round(score, 4),
                "match": "semantic",
            })
        if not scored:
            out = self.search(query, ns=ns, limit=limit)
            for o in out:
                o["match"] = "like_fallback"
            return out
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    def backfill_embeddings(self, ns: Optional[str] = None,
                            limit: int = 200) -> dict:
        """Embeda em lote entradas antigas sem embedding. Aborta no primeiro
        None (embedder offline) para nao pagar N timeouts em vao."""
        sql = "SELECT ns, key, value FROM kv WHERE embedding IS NULL"
        params: list[Any] = []
        if ns:
            sql += " AND ns=?"
            params.append(ns)
        sql += " LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        ok = 0
        for ns_, k, v in rows:
            blob = self._embed_blob(f"{k}: {v}")
            if blob is None:
                break
            with self._connect() as conn:
                conn.execute("UPDATE kv SET embedding=? WHERE ns=? AND key=?",
                             (blob, ns_, k))
                conn.commit()
            ok += 1
        return {"embedded": ok, "pendentes": len(rows) - ok}

    # ---- manutencao ---------------------------------------------------------

    def cleanup_expired(self) -> int:
        """Remove todas as entradas expiradas. Retorna quantas foram removidas."""
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM kv WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
            conn.commit()
            n = cur.rowcount
        if n:
            log.info("Removidas %d entradas expiradas", n)
        return n

    def clear_namespace(self, ns: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM kv WHERE ns=?", (ns,))
            conn.commit()
            return cur.rowcount

    def stats(self) -> dict:
        """Retorna estatisticas: total, por ns, expirados, tamanho do DB."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
            by_ns = dict(conn.execute(
                "SELECT ns, COUNT(*) FROM kv GROUP BY ns ORDER BY 2 DESC"
            ).fetchall())
            now = datetime.now().isoformat()
            expired = conn.execute(
                "SELECT COUNT(*) FROM kv WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            ).fetchone()[0]
            with_emb = conn.execute(
                "SELECT COUNT(*) FROM kv WHERE embedding IS NOT NULL"
            ).fetchone()[0]
        return {
            "total": total,
            "by_namespace": by_ns,
            "expired": expired,
            "with_embedding": with_emb,
            "db_path": str(self.db_path),
            "db_size_bytes": (
                self.db_path.stat().st_size if self.db_path.exists() else 0
            ),
            "schema_version": SCHEMA_VERSION,
        }

    # ---- export/import (backup) --------------------------------------------

    def export_json(self, ns: Optional[str] = None) -> str:
        """Exporta entradas como JSON (string). Se ns=None, exporta tudo."""
        rows = self.list(ns=ns, include_expired=True)
        return json.dumps(
            {"exported_at": datetime.now().isoformat(), "entries": rows},
            ensure_ascii=False, indent=2,
        )

    def import_json(self, data: str, overwrite: bool = False) -> int:
        """Importa JSON exportado. Retorna numero de entradas importadas."""
        parsed = json.loads(data) if isinstance(data, str) else data
        entries = parsed.get("entries", []) if isinstance(parsed, dict) else parsed
        n = 0
        for e in entries:
            if not overwrite and self.get(
                    e["key"], ns=e.get("ns", "default"), default=None) is not None:
                continue
            self.set(
                e["key"],
                e["value"],
                ns=e.get("ns", "default"),
                tags=e.get("tags", ""),
            )
            n += 1
        log.info("Importadas %d entradas (overwrite=%s)", n, overwrite)
        return n


# -- Singleton -----------------------------------------------------------------
_instance: Optional[KVMemory] = None


def get_memory() -> KVMemory:
    global _instance
    if _instance is None:
        _instance = KVMemory()
    return _instance


def reset_singleton() -> None:
    """Util para testes ou se DB_PATH mudar em runtime."""
    global _instance
    _instance = None

