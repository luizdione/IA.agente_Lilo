"""
tests/test_routing_golden.py -- Golden-set de roteamento (F3).

Trava a acurácia do roteador (shared/router.py) contra regressões nas ASSINATURAS
(description/keywords via capabilities()) dos agentes. O modo keyword é
determinístico e roda sempre; o modo embed precisa do modelo sentence-transformers
-> só roda com LILO_TEST_EMBED=1 (evita baixar/carregar modelo no check.py).

Baseline 2026-07-23 (após desambiguação das assinaturas): keyword 15/18, embed 15/18.
"""
from __future__ import annotations

import os
import pytest

# (query, agente_esperado) -- domínios reais do dono.
GOLDEN = [
    ("conte quantas linhas tem a tabela animais no banco sqlite", "sql"),
    ("gere uma query SELECT somando registros por especie", "sql"),
    ("resuma este artigo em pdf destacando objetivo e conclusao", "pdf"),
    ("extraia a secao de metodos deste paper", "pdf"),
    ("busque artigos no pubmed sobre babesia bovis em bovinos", "scholar"),
    ("encontre papers recentes sobre docking molecular de inibidores", "scholar"),
    ("faca um ANOVA comparando os grupos tratado e controle", "prism"),
    ("teste de normalidade shapiro-wilk e boxplot dos meus dados", "prism"),
    ("escreva a introducao do meu manuscrito cientifico", "paper"),
    ("redija a discussao do paper para submissao na revista", "paper"),
    ("gere uma planilha xlsx com esses dados tabulares", "docgen"),
    ("crie uma apresentacao pptx a partir deste outline", "docgen"),
    ("liste os arquivos python da pasta do projeto", "desktop"),
    ("rode este script e me diga a saida", "desktop"),
    ("crie um novo subagente para converter imagens", "skillsmith"),
    ("gere o scaffold de um agente novo chamado foo", "skillsmith"),
    ("o que e fotossintese?", "gateway"),
    ("explique brevemente o que e uma API REST", "gateway"),
]


def _caps():
    """{nome: capabilities()} dos agentes reais (usa o mesmo path do runtime)."""
    from lilo import _load_agents
    agents = _load_agents()
    return {n: a.capabilities() for n, a in agents.items()}


def _accuracy(mode: str) -> int:
    os.environ["LILO_ROUTER"] = mode
    from shared import router
    router._EMBED_CACHE.clear()
    caps = _caps()
    avail = set(caps)
    return sum(
        router.route_query(q, caps, available=avail).target == exp
        for q, exp in GOLDEN
    )


def test_keyword_routing_nao_regride():
    # Baseline 15/18; exigimos >=14 (margem de 1) para pegar regressão de assinatura.
    assert _accuracy("keyword") >= 14


@pytest.mark.skipif(not os.getenv("LILO_TEST_EMBED"),
                    reason="modo embed precisa do modelo; ligue com LILO_TEST_EMBED=1")
def test_embed_routing_nao_regride():
    os.environ.setdefault("LILO_ROUTER_THRESHOLD", "0.35")
    assert _accuracy("embed") >= 13
