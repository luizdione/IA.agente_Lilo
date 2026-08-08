"""tests/shared/test_memory_facade.py — V18.4 E3: fachada unificada.

Offline: KV com embedder fake (singleton monkeypatchado) e chat_memory
substituido por stub. Cobre: gate de voz no inject, combinacao KV+notas+chats
no recall e o handler MCP lilo_recall.
"""
from __future__ import annotations

import shared.kv_memory as kvmod
from shared.kv_memory import KVMemory
from shared.memory_facade import get_relevant_context, recall

VOCAB = ("bioinformatica", "genoma", "docker", "musica")


def _fake_embedder(text):
    t = str(text).lower()
    return [float(t.count(w)) for w in VOCAB]


class _StubChat:
    def build_project_context(self, project_id, max_chars=3000):
        return "## Estado atual\n- migracao do pipeline concluida"

    def search_chats(self, query, limit=20):
        return [{"title": "Chat sobre genoma", "subagent": "gateway",
                 "updated_at": "2026-08-04"}]


def _prepara(tmp_path, monkeypatch, nome="kv.db"):
    m = KVMemory(db_path=tmp_path / nome)
    m.embedder = _fake_embedder
    monkeypatch.setattr(kvmod, "_instance", m)
    monkeypatch.setattr("shared.chat_memory.get_memory",
                        lambda db_path=None: _StubChat())
    m.set("nota_bio", "descoberta sobre genoma bovino", ns="user")
    return m


def test_inject_respeita_gate_de_voz(tmp_path, monkeypatch):
    _prepara(tmp_path, monkeypatch)
    # sem owner_verified e sem projeto -> nada e injetado
    assert get_relevant_context("genoma") == ""
    # com owner_verified -> memoria do dono entra, marcada como DADO
    bloco = get_relevant_context("genoma", owner_verified=True)
    assert "nota_bio" in bloco and "DADOS de referencia" in bloco
    assert "[Fim da memoria]" in bloco


def test_inject_projeto_traz_notes(tmp_path, monkeypatch):
    _prepara(tmp_path, monkeypatch, "kv2.db")
    bloco = get_relevant_context("qualquer", project_id="proj1")
    assert "notes.md" in bloco and "migracao do pipeline" in bloco


def test_recall_combina_kv_notas_e_chats(tmp_path, monkeypatch):
    _prepara(tmp_path, monkeypatch, "kv3.db")
    out = recall("genoma", project_id="proj1")
    assert "KV [user/nota_bio]" in out
    assert "notes.md:" in out
    assert "Chat sobre genoma" in out


def test_handler_mcp_lilo_recall(tmp_path, monkeypatch):
    _prepara(tmp_path, monkeypatch, "kv4.db")
    from lilo import handle_tool_call
    out = handle_tool_call("lilo_recall", {"query": "genoma"})
    assert "[recall]" in out and "nota_bio" in out
    assert "obrigatorio" in handle_tool_call("lilo_recall", {"query": ""})
