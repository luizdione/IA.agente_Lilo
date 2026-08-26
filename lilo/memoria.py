"""Memoria longa do LILO — KV em SQLite (WAL) com busca SEMANTICA opcional.

Herda do kv_memory do legado o que provou valor: WAL + busy_timeout, DB fora
do repo/OneDrive e o desenho embed-com-fallback (v13.2): o embedding e
calculado NO GRAVAR via /api/embed (best-effort, timeout curto — embedder
fora do ar degrada silenciosamente) e a busca semantica faz cosseno em Python
puro (escala pessoal; sem numpy no runtime), caindo para LIKE quando nao ha
embeddings ou nada pontua. Exposta pelas tools memorizar/lembrar/esquecer,
atras do choke-point como qualquer outra.
"""
from __future__ import annotations

import math
import sqlite3
from array import array
from datetime import datetime, timezone
from pathlib import Path

from lilo import config

EMBED_TIMEOUT_S = 3.0
MIN_SCORE = 0.35  # abaixo disso a semantica nao "acha" — cai p/ LIKE


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
    # v13.2: coluna de embedding (migracao no padrao _ensure_column do legado)
    cols = {linha[1] for linha in con.execute("PRAGMA table_info(kv)")}
    if "embedding" not in cols:
        con.execute("ALTER TABLE kv ADD COLUMN embedding BLOB")
    con.commit()
    return con


# --- embeddings (best-effort; nunca derrubam a memoria) ---------------------
def _embed(texto: str) -> list[float] | None:
    """Vetor via POST /api/embed, ou None (desligado/offline/erro)."""
    if not config.memoria_embed():
        return None
    try:
        import requests
        r = requests.post(config.ollama_host() + "/api/embed",
                          json={"model": config.modelo_embed(),
                                "input": texto[:2000]},
                          timeout=EMBED_TIMEOUT_S)
        r.raise_for_status()
        vetores = r.json().get("embeddings") or []
        return list(vetores[0]) if vetores else None
    except Exception:  # noqa: BLE001 — embedder e opcional por design
        return None


def _pack(vetor: list[float]) -> bytes:
    return array("f", vetor).tobytes()


def _unpack(blob: bytes) -> list[float]:
    a = array("f")
    a.frombytes(blob)
    return list(a)


def _cosseno(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gravar(chave: str, valor: str, tags: str = "") -> None:
    vetor = _embed("%s: %s %s" % (chave, valor, tags))
    with _connect() as con:
        con.execute(
            "INSERT INTO kv (chave, valor, tags, criado_em, atualizado_em, "
            "embedding) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(chave) DO "
            "UPDATE SET valor=excluded.valor, tags=excluded.tags, "
            "atualizado_em=excluded.atualizado_em, "
            "embedding=excluded.embedding",
            (chave.strip(), valor, tags.strip(), _agora(), _agora(),
             _pack(vetor) if vetor else None))


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


def buscar_semantica(termo: str, limite: int = 8) -> list[tuple[str, str, str]]:
    """[(chave, valor, tags)] por cosseno sobre as linhas com embedding.
    Vazio quando o embedder esta fora/desligado ou nada passa de MIN_SCORE."""
    consulta = _embed(termo)
    if not consulta:
        return []
    with _connect() as con:
        linhas = con.execute("SELECT chave, valor, tags, embedding FROM kv "
                             "WHERE embedding IS NOT NULL").fetchall()
    pontuadas = []
    for chave, valor, tags, blob in linhas:
        score = _cosseno(consulta, _unpack(blob))
        if score >= MIN_SCORE:
            pontuadas.append((score, chave, valor, tags))
    pontuadas.sort(reverse=True)
    return [(c, v, t) for _, c, v, t in pontuadas[:limite]]


def buscar_inteligente(termo: str, limite: int = 8) -> list[tuple[str, str, str]]:
    """Semantica primeiro; completa/cai para LIKE. Sem duplicatas."""
    achados = buscar_semantica(termo, limite)
    vistos = {c for c, _, _ in achados}
    for linha in buscar(termo, limite):
        if linha[0] not in vistos and len(achados) < limite:
            achados.append(linha)
            vistos.add(linha[0])
    return achados


def apagar(chave: str) -> bool:
    with _connect() as con:
        return con.execute("DELETE FROM kv WHERE chave = ?",
                           (chave.strip(),)).rowcount > 0


def listar(limite: int = 20) -> list[tuple[str, str, str]]:
    """[(chave, valor, tags)] mais recentes primeiro (p/ \\memoria no REPL)."""
    with _connect() as con:
        return con.execute(
            "SELECT chave, valor, tags FROM kv ORDER BY atualizado_em DESC "
            "LIMIT ?", (limite,)).fetchall()
