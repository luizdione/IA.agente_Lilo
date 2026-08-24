"""tests/shared/test_kv_semantic.py — V18.3 E2: busca semantica no KV.

Offline: embedder FAKE deterministico (contagem de termos de um vocabulario)
injetado via KVMemory.embedder — nenhuma chamada ao Ollama. Cobre: ranking
por significado, fallback textual transparente, backfill de linhas antigas,
migracao de schema v2 -> v3 e contagem em stats().
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from shared.kv_memory import KVMemory

VOCAB = ("bioinformatica", "genoma", "docker", "container", "musica")


def _fake_embedder(text):
    t = str(text).lower()
    return [float(t.count(w)) for w in VOCAB]


def _mem(tmp_path, nome="kv.db"):
    m = KVMemory(db_path=tmp_path / nome)
    m.embedder = _fake_embedder
    return m


def test_semantica_encontra_por_significado(tmp_path):
    m = _mem(tmp_path)
    m.set("nota_bio", "pipeline de genoma e bioinformatica", ns="user")
    m.set("nota_dev", "subir container docker do dashboard", ns="user")
    out = m.search_semantic("analise de genoma bioinformatica", ns="user")
    assert out and out[0]["key"] == "nota_bio"
    assert out[0]["match"] == "semantic" and out[0]["score"] > 0.5
    # o item de docker nao deve ranquear para query de genoma
    assert all(o["key"] != "nota_dev" for o in out)


def test_fallback_textual_sem_embedder(tmp_path):
    m = KVMemory(db_path=tmp_path / "kv2.db")
    m.embedder = lambda text: None  # simula Ollama offline
    m.set("chave", "valor com docker dentro", ns="user")
    out = m.search_semantic("docker", ns="user")
    assert out and out[0]["match"] == "like_fallback"


def test_backfill_embeda_linhas_antigas(tmp_path):
    m = _mem(tmp_path, "kv3.db")
    now = datetime.now().isoformat()
    with m._connect() as c:
        c.execute(
            "INSERT INTO kv (ns, key, value, tags, created_at, updated_at) "
            "VALUES ('user', 'velha', 'texto sobre genoma', '', ?, ?)",
            (now, now))
        c.commit()
    r = m.backfill_embeddings(ns="user")
    assert r["embedded"] == 1 and r["pendentes"] == 0
    out = m.search_semantic("genoma", ns="user")
    assert any(o["key"] == "velha" and o["match"] == "semantic" for o in out)


def test_migracao_adiciona_coluna_em_db_v2(tmp_path):
    db = tmp_path / "legado.db"
    with sqlite3.connect(db) as c:
        c.execute(
            "CREATE TABLE kv (ns TEXT NOT NULL DEFAULT 'default', "
            "key TEXT NOT NULL, value TEXT NOT NULL, tags TEXT DEFAULT '', "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "expires_at TEXT, PRIMARY KEY (ns, key))")
        c.commit()
    KVMemory(db_path=db)  # init roda a migracao incremental
    cols = [r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(kv)")]
    assert "embedding" in cols


def test_stats_conta_embeddings(tmp_path):
    m = _mem(tmp_path, "kv4.db")
    m.set("a", "bioinformatica aplicada", ns="user")
    st = m.stats()
    assert st["with_embedding"] >= 1


def test_handler_mcp_formata_resultado(tmp_path, monkeypatch):
    # handle_tool_call usa o singleton -> injeta um KVMemory de teste.
    import shared.kv_memory as kvmod
    m = _mem(tmp_path, "kv5.db")
    monkeypatch.setattr(kvmod, "_instance", m)
    m.set("nota_bio", "pipeline de genoma", ns="user")
    from lilo import handle_tool_call
    out = handle_tool_call("lilo_memory_semantic_search",
                           {"query": "genoma", "namespace": "user"})
    assert "[semantica]" in out and "nota_bio" in out and "score" in out
