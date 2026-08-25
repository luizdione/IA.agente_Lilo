"""Memoria longa do LILO v13.1 — KV minimo em SQLite (WAL), sem embeddings.

Herda do kv_memory do legado apenas o que provou valor: WAL + busy_timeout e
o DB fora do repo/OneDrive. Busca por LIKE (chave/valor/tags) — semantica por
embedding fica para quando houver caso de uso (a licao anti-inchaco vale
tambem para dentro do nucleo). Exposta ao modelo pelas tools memorizar/
lembrar, atras do choke-point como qualquer outra.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from lilo import config


def _db_path() -> Path:
    override = config.get_env("LILO_MEMORIA_DB", "")
    return Path(override) if override else config.dir_dados() / "memoria.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("""CREATE TABLE IF NOT EXISTS kv (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '',
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL)""")
    con.commit()
    return con


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gravar(chave: str, valor: str, tags: str = "") -> None:
    with _connect() as con:
        con.execute(
            "INSERT INTO kv (chave, valor, tags, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(chave) DO UPDATE SET "
            "valor=excluded.valor, tags=excluded.tags, "
            "atualizado_em=excluded.atualizado_em",
            (chave.strip(), valor, tags.strip(), _agora(), _agora()))


def obter(chave: str) -> str | None:
    with _connect() as con:
        linha = con.execute("SELECT valor FROM kv WHERE chave = ?",
                            (chave.strip(),)).fetchone()
    return linha[0] if linha else None


def buscar(termo: str, limite: int = 8) -> list[tuple[str, str, str]]:
    """[(chave, valor, tags)] com LIKE em chave/valor/tags, mais recentes
    primeiro."""
    like = "%" + termo.strip() + "%"
    with _connect() as con:
        return con.execute(
            "SELECT chave, valor, tags FROM kv WHERE chave LIKE ? OR "
            "valor LIKE ? OR tags LIKE ? ORDER BY atualizado_em DESC LIMIT ?",
            (like, like, like, limite)).fetchall()


def apagar(chave: str) -> bool:
    with _connect() as con:
        return con.execute("DELETE FROM kv WHERE chave = ?",
                           (chave.strip(),)).rowcount > 0
