"""Regression tests for shared/kv_memory.py.

Cobre o caminho-feliz e o caso da SyntaxError detectada no relatorio de
2026-05-13 (bloco singleton duplicado/quebrado). Estes testes nao usam
LLM, sao deterministicos e seguros para CI.

Executar:
    pytest tests/shared/test_kv_memory.py -v
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_kv(tmp_path, monkeypatch):
    """Forca KVMemory a usar um SQLite isolado em tmp_path."""
    db = tmp_path / "kv.sqlite"
    monkeypatch.setenv("LILO_KV_MEMORY_DB", str(db))

    from shared import kv_memory as kvm
    kvm.reset_singleton()

    mem = kvm.KVMemory(db_path=db)
    yield mem

    kvm.reset_singleton()


# ---------------------------------------------------------------------------
# Smoke / import
# ---------------------------------------------------------------------------

def test_module_importable():
    """Regressao do SyntaxError corrigido em 2026-05-13 (linha 402)."""
    import shared.kv_memory as kvm  # noqa: F401
    assert hasattr(kvm, "KVMemory")
    assert hasattr(kvm, "get_memory")
    assert hasattr(kvm, "reset_singleton")


def test_singleton_is_unique(tmp_path, monkeypatch):
    db = tmp_path / "kv_singleton.sqlite"
    monkeypatch.setenv("LILO_KV_MEMORY_DB", str(db))
    from shared import kv_memory as kvm
    kvm.reset_singleton()
    a = kvm.get_memory()
    b = kvm.get_memory()
    assert a is b


# ---------------------------------------------------------------------------
# CRUD basico
# ---------------------------------------------------------------------------

def test_set_get_roundtrip(tmp_kv):
    tmp_kv.set("k1", "v1", ns="test")
    assert tmp_kv.get("k1", ns="test") == "v1"


def test_get_default_for_missing(tmp_kv):
    assert tmp_kv.get("nao_existe", ns="test", default="fallback") == "fallback"


def test_delete_returns_bool(tmp_kv):
    tmp_kv.set("k", "v", ns="test")
    assert tmp_kv.delete("k", ns="test") is True
    assert tmp_kv.delete("k", ns="test") is False


def test_overwrite_updates_value(tmp_kv):
    tmp_kv.set("k", "v1", ns="test")
    tmp_kv.set("k", "v2", ns="test")
    assert tmp_kv.get("k", ns="test") == "v2"


def test_complex_value_serialization(tmp_kv):
    """set() auto-serializa dicts/lists; get() auto-desserializa."""
    payload = {"a": 1, "b": [1, 2, 3]}
    tmp_kv.set("c", payload, ns="test")
    assert tmp_kv.get("c", ns="test") == payload


# ---------------------------------------------------------------------------
# Namespacing
# ---------------------------------------------------------------------------

def test_namespace_isolation(tmp_kv):
    tmp_kv.set("k", "a", ns="ns_a")
    tmp_kv.set("k", "b", ns="ns_b")
    assert tmp_kv.get("k", ns="ns_a") == "a"
    assert tmp_kv.get("k", ns="ns_b") == "b"


def test_list_filters_by_namespace(tmp_kv):
    tmp_kv.set("k1", "v", ns="ns_a")
    tmp_kv.set("k2", "v", ns="ns_a")
    tmp_kv.set("k3", "v", ns="ns_b")
    rows = tmp_kv.list(ns="ns_a")
    keys = {r["key"] for r in rows}
    assert keys == {"k1", "k2"}


# ---------------------------------------------------------------------------
# Search / export / import
# ---------------------------------------------------------------------------

def test_search_finds_substring(tmp_kv):
    tmp_kv.set("modelo", "claude-sonnet-4-5", ns="user")
    tmp_kv.set("outro", "valor qualquer", ns="user")
    hits = tmp_kv.search("claude")
    assert any(h["key"] == "modelo" for h in hits)


def test_export_import_roundtrip(tmp_kv, tmp_path, monkeypatch):
    tmp_kv.set("k1", "v1", ns="backup")
    tmp_kv.set("k2", "v2", ns="backup")
    blob = tmp_kv.export_json(ns="backup")
    assert "k1" in blob and "v2" in blob

    db2 = tmp_path / "kv2.sqlite"
    monkeypatch.setenv("LILO_KV_MEMORY_DB", str(db2))
    from shared import kv_memory as kvm
    kvm.reset_singleton()
    mem2 = kvm.KVMemory(db_path=db2)
    n = mem2.import_json(blob)
    assert n >= 2
    assert mem2.get("k1", ns="backup") == "v1"
    assert mem2.get("k2", ns="backup") == "v2"


# ---------------------------------------------------------------------------
# TTL / cleanup
# ---------------------------------------------------------------------------

def test_cleanup_expired_removes_old(tmp_kv):
    """Forca expires_at no passado e roda cleanup_expired."""
    tmp_kv.set("ephemeral", "x", ns="test", ttl_seconds=3600)
    past = (datetime.now() - timedelta(seconds=10)).isoformat()
    with sqlite3.connect(str(tmp_kv.db_path)) as conn:
        conn.execute(
            "UPDATE kv SET expires_at=? WHERE ns=? AND key=?",
            (past, "test", "ephemeral"),
        )
        conn.commit()
    removed = tmp_kv.cleanup_expired()
    assert removed >= 1
    assert tmp_kv.get("ephemeral", ns="test") is None
