"""Sessoes do LILO v13 — transcript persistente em SQLite.

Herancas do legado (v12.15-legado): _connect com WAL + synchronous=NORMAL +
busy_timeout (kv_memory.py — sem isso um loop que grava a cada iteracao
trava com "database is locked") e DB SEMPRE fora do repo/OneDrive
(%LOCALAPPDATA%\\LILO no Windows). Correcao do v13: as colunas tool_calls e
tool_name reidratam o array messages[] FIELMENTE — o legado achatava o
historico em string porque o cliente so aceitava 2 mensagens.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from lilo import config


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.sessions_db())
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=5000")
    _schema(con)
    return con


def _schema(con: sqlite3.Connection) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        titulo TEXT NOT NULL DEFAULT '',
        cwd TEXT NOT NULL DEFAULT '',
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL DEFAULT '',
        tool_name TEXT,
        tool_calls TEXT,
        criado_em TEXT NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES chats(id))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_msg_chat ON messages(chat_id, seq)")
    con.commit()


def _agora() -> str:
    # Microssegundos: duas gravacoes no mesmo SEGUNDO nao podem empatar a
    # ordenacao de "sessao mais recente".
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def nova_sessao(cwd: str = "") -> str:
    chat_id = uuid.uuid4().hex[:12]
    with _connect() as con:
        con.execute("INSERT INTO chats (id, cwd, criado_em, atualizado_em) "
                    "VALUES (?, ?, ?, ?)", (chat_id, cwd, _agora(), _agora()))
    return chat_id


def gravar(chat_id: str, msgs: list[dict]) -> None:
    """Persiste o transcript INTEIRO da conversa (substitui o anterior).

    Chamado a cada iteracao do loop — com WAL, um kill no meio deixa o
    ultimo estado consistente gravado. Titulo = 1a mensagem de usuario."""
    titulo = next((m.get("content", "")[:80] for m in msgs
                   if m.get("role") == "user"), "")
    with _connect() as con:
        con.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        for seq, m in enumerate(msgs):
            con.execute(
                "INSERT INTO messages (chat_id, seq, role, content, "
                "tool_name, tool_calls, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chat_id, seq, m.get("role", ""), m.get("content") or "",
                 m.get("tool_name"),
                 json.dumps(m["tool_calls"], ensure_ascii=False)
                 if m.get("tool_calls") else None,
                 _agora()))
        con.execute("UPDATE chats SET titulo = ?, atualizado_em = ? "
                    "WHERE id = ?", (titulo, _agora(), chat_id))


def carregar(chat_id: str) -> list[dict]:
    """Reidrata o messages[] fielmente (incluindo tool_calls/tool_name)."""
    with _connect() as con:
        linhas = con.execute(
            "SELECT role, content, tool_name, tool_calls FROM messages "
            "WHERE chat_id = ? ORDER BY seq", (chat_id,)).fetchall()
    msgs: list[dict] = []
    for role, content, tool_name, tool_calls in linhas:
        m: dict = {"role": role, "content": content}
        if tool_name:
            m["tool_name"] = tool_name
        if tool_calls:
            try:
                m["tool_calls"] = json.loads(tool_calls)
            except (json.JSONDecodeError, ValueError):
                pass
        msgs.append(m)
    return msgs


def ultima_sessao() -> str | None:
    with _connect() as con:
        linha = con.execute(
            "SELECT id FROM chats ORDER BY atualizado_em DESC, rowid DESC "
            "LIMIT 1").fetchone()
    return linha[0] if linha else None


def carregar_ultima() -> list[dict] | None:
    """Transcript da sessao mais recente, ou None se nao houver."""
    chat_id = ultima_sessao()
    return carregar(chat_id) if chat_id else None
