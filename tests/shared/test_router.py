"""Testes do roteador único (shared/router.py).

Cobrem o modo keyword (default, offline) e o fallback do modo embed quando o
stack de embeddings está indisponível. O teste de embed REAL é opcional
(LILO_TEST_EMBED=1) para não baixar/instanciar o modelo no check.py.
"""
from __future__ import annotations

import os
import pytest

from shared.router import (
    RouteDecision,
    agent_signature,
    route_query,
    _keyword_route,
)

# Agentes sintéticos (determinísticos, independentes do runtime) no formato
# capabilities(): {name, description, keywords}.
AGENTS = {
    "sql": {
        "name": "sql",
        "description": "Consulta e estatística em banco de dados SQLite/MySQL.",
        "keywords": ["sql", "select", "tabela", "banco", "query"],
    },
    "prism": {
        "name": "prism",
        "description": "Análise estatística científica e gráficos de publicação.",
        "keywords": ["anova", "t-test", "boxplot", "normalidade", "comparar grupos"],
    },
    "scholar": {
        "name": "scholar",
        "description": "Busca acadêmica em PubMed e arXiv.",
        "keywords": ["pubmed", "arxiv", "literatura", "papers"],
    },
    "gateway": {
        "name": "gateway",
        "description": "Chat geral e dúvidas rápidas.",
        "keywords": ["explique", "o que e", "conceito"],
    },
    "villa": {
        "name": "villa",
        "description": "Orquestrador multi-etapa.",
        "keywords": ["orquestrar", "pipeline", "multi-agente"],
    },
}


@pytest.fixture(autouse=True)
def _keyword_mode(monkeypatch):
    """Garante modo keyword por padrão (offline, determinístico)."""
    monkeypatch.setenv("LILO_ROUTER", "keyword")


def test_route_decision_shape():
    d = RouteDecision(target="sql", method="keyword")
    assert d.target == "sql"
    assert d.method == "keyword"
    assert d.score == 0.0
    assert d.scores == {}
    assert d.reason == ""


def test_agent_signature_combina_nome_desc_keywords():
    sig = agent_signature(AGENTS["sql"])
    assert "sql" in sig and "banco" in sig and "estatística" in sig.lower()


def test_keyword_route_escolhe_especialista():
    d = route_query("gere um SELECT para contar registros na tabela genomas", AGENTS)
    assert d.target == "sql"
    assert d.method == "keyword"
    assert d.scores["sql"] >= 1


def test_keyword_route_prism():
    d = route_query("preciso comparar grupos com um ANOVA e um boxplot", AGENTS)
    assert d.target == "prism"
    assert d.method == "keyword"


def test_fronteira_de_palavra_nao_casa_substring():
    # 'select' não deve casar dentro de "selecionar" (fronteira de palavra).
    _, scores = _keyword_route("preciso selecionar uma abordagem", AGENTS)
    assert scores.get("sql", 0) == 0


def test_villa_nunca_e_alvo_keyword():
    # Mesmo citando "pipeline", villa é ignorado como especialista keyword.
    _, scores = _keyword_route("montar um pipeline de orquestrar", AGENTS)
    assert "villa" not in scores


def test_ambiguo_cai_no_gateway():
    d = route_query("xyzzy blargh qwerty", AGENTS)
    assert d.target == "gateway"
    assert d.method == "ambiguous"


def test_dominio_indisponivel_vai_para_villa():
    # sql casa, mas não está disponível -> pipeline (villa), como no route_target.
    d = route_query("SELECT * FROM tabela", AGENTS, available={"prism", "gateway", "villa"})
    assert d.target == "villa"
    assert d.method == "unavailable"


def test_embed_falha_cai_no_keyword(monkeypatch):
    """Se o modo embed lançar exceção, route_query degrada para keyword."""
    monkeypatch.setenv("LILO_ROUTER", "embed")

    def _boom(_agents):
        raise RuntimeError("sentence-transformers indisponível (teste)")

    monkeypatch.setattr("shared.router._get_embed_router", _boom)
    d = route_query("gere um SELECT na tabela", AGENTS)
    assert d.target == "sql"
    assert d.method == "keyword"  # provou o fallback


@pytest.mark.skipif(
    not os.getenv("LILO_TEST_EMBED"),
    reason="teste de embed real (baixa/instancia o modelo); ligue com LILO_TEST_EMBED=1",
)
def test_embed_real_roteia_sem_crash(monkeypatch):
    monkeypatch.setenv("LILO_ROUTER", "embed")
    d = route_query("faça uma análise estatística ANOVA no meu csv", AGENTS)
    assert isinstance(d, RouteDecision)
    assert d.method in ("embed", "keyword")  # embed ou fallback, mas sem crashar
    assert d.target in set(AGENTS) | {"gateway"}
