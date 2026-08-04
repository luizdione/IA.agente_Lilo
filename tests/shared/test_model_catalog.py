"""tests/shared/test_model_catalog.py — V18 H2: E1 (catalogo) + E4 + E5.

Offline (sem rede/LLM). Cobre:
  - E1: catalogo central de modelos (provedores, heuristicas, precos, missing)
  - E4: sintese de diretorio le CLAUDE.md/TASKS.md e docs//prompts/
  - E5: gate de privacidade pre-cloud (cloud_send) por modo de execucao
"""
from __future__ import annotations

import pytest

from shared import exec_mode
from shared.llm_client import _cloud_gate, _maybe_cloud_gate
from shared.model_catalog import (
    PROVIDER_ANTHROPIC, PROVIDER_OLLAMA, PROVIDER_OLLAMA_CLOUD,
    anthropic_prices_mtok, get_model_info, is_cloud_model, missing_models)


# ── E1: catalogo ─────────────────────────────────────────────────────────────

def test_catalogo_conhece_defaults_do_lilo():
    assert get_model_info("gpt-oss:120b-cloud").provider == PROVIDER_OLLAMA_CLOUD
    assert get_model_info("llama3.1:8b-instruct-q8_0").provider == PROVIDER_OLLAMA
    assert get_model_info("claude-sonnet-4-5").provider == PROVIDER_ANTHROPIC


def test_heuristica_sufixo_cloud_e_is_cloud():
    assert get_model_info("modelo-novo-cloud").provider == PROVIDER_OLLAMA_CLOUD
    assert is_cloud_model("modelo-novo-cloud") is True
    assert is_cloud_model("claude-haiku-4-5") is True
    assert is_cloud_model("qwen2.5-coder:14b") is False


def test_precos_anthropic_por_familia_e_fail_safe():
    assert anthropic_prices_mtok("claude-haiku-4-5") == (1.0, 5.0)
    assert anthropic_prices_mtok("claude-sonnet-4-5") == (3.0, 15.0)
    # Familia desconhecida -> preco Opus (superestima; fail-safe p/ budget)
    assert anthropic_prices_mtok("claude-familia-nova") == (5.0, 25.0)


def test_missing_models_ignora_cloud_e_anthropic():
    configured = ["llama3.1:8b-instruct-q8_0", "gpt-oss:120b-cloud",
                  "claude-sonnet-4-5", "modelo-inexistente:7b"]
    installed = ["llama3.1:8b-instruct-q8_0"]
    assert missing_models(configured, installed) == ["modelo-inexistente:7b"]


def test_missing_models_aceita_match_por_nome_base():
    # instalado com outra tag -> nao acusar ausencia
    assert missing_models(["qwen2.5-coder:14b"], ["qwen2.5-coder:latest"]) == []


# ── E5: gate pre-cloud ───────────────────────────────────────────────────────

@pytest.fixture()
def _modo_restaurado():
    antes = exec_mode.get_mode()
    exec_mode._GRANT = False  # estado global de processo: zera grant pendente
    exec_mode.clear_plan()
    yield
    exec_mode.set_mode(antes)
    exec_mode.clear_plan()


def test_cloud_gate_auto_passa(_modo_restaurado):
    exec_mode.set_mode("auto")
    assert _cloud_gate("anthropic", "claude-sonnet-4-5", 123) is None


def test_cloud_gate_ask_pede_confirmacao(_modo_restaurado):
    exec_mode.set_mode("ask")
    out = _cloud_gate("anthropic", "claude-sonnet-4-5", 123)
    assert out is not None and exec_mode.is_confirm(out)


def test_cloud_gate_plan_bloqueia_e_acumula(_modo_restaurado):
    exec_mode.set_mode("plan")
    out = _cloud_gate("ollama_cloud", "gpt-oss:120b-cloud", 50)
    assert out is not None and exec_mode.is_block(out)
    assert any(i["kind"] == "cloud_send" for i in exec_mode.pending_plan())


def test_cloud_gate_kill_switch(monkeypatch, _modo_restaurado):
    exec_mode.set_mode("ask")
    monkeypatch.setenv("LILO_CLOUD_GATE", "0")
    assert _cloud_gate("anthropic", "claude-sonnet-4-5", 10) is None


def test_maybe_cloud_gate_ignora_modelo_local(_modo_restaurado):
    # Modelo local nunca passa pelo gate, mesmo em modo ask.
    exec_mode.set_mode("ask")
    assert _maybe_cloud_gate("llama3.1:8b-instruct-q8_0", "p", "s") is None


# ── E4: memoria de projeto na sintese ────────────────────────────────────────

def test_sintese_inclui_claude_md_e_docs(tmp_path):
    from shared.dir_synthesis import synthesize_directory
    (tmp_path / "CLAUDE.md").write_text("# Regras do projeto X", encoding="utf-8")
    (tmp_path / "TASKS.md").write_text("- [ ] tarefa pendente", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "visao.md").write_text("Visao geral do sistema", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "persona.md").write_text("Persona do agente", encoding="utf-8")

    out = synthesize_directory(tmp_path, out_dir=tmp_path / "_synth",
                               include_tree=False, include_todos=False,
                               include_git=False)
    text = out.read_text(encoding="utf-8")
    assert "CLAUDE.md" in text and "Regras do projeto X" in text
    assert "TASKS.md" in text and "tarefa pendente" in text
    assert "Memoria do projeto" in text
    assert "visao.md" in text and "Visao geral do sistema" in text
    assert "persona.md" in text and "Persona do agente" in text
