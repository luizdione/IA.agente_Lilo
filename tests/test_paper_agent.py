"""
tests/test_paper_agent.py — Cobertura OFFLINE do PaperAgent (V13).

Sem rede e sem LLM: valida estrutura (tools/health/capabilities), a formatacao
de referencias e a regra anti-invencao (sem refs -> sinaliza lacuna, nunca
fabrica). A redacao real (cloud) e a busca de refs (rede) sao validadas
manualmente/e2e, nao aqui.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def paper():
    from agents.paper.agent import PaperAgent
    return PaperAgent()


def test_tools_present(paper):
    names = {t["name"] for t in paper.get_tools()}
    assert {"paper_outline", "paper_section", "paper_references",
            "paper_draft", "paper_build"} <= names


def test_health_reports_writer_and_skill(paper):
    h = paper.health()
    assert h["status"] == "ok"
    assert h["writer_model"]            # modelo do escritor definido
    assert h["skill_present"] is True   # skill portada para o LILO
    assert h["build_sh"] is True        # build.sh disponivel


def test_capabilities_structure(paper):
    c = paper.capabilities()
    assert c["name"] == "paper"
    assert "abstract" in c["sections"] and "discussao" in c["sections"]
    assert c["keywords"]


def test_fmt_refs_empty_signals_gap_never_fabricates(paper):
    # Sem referencias: o agente deve SINALIZAR a lacuna, jamais inventar.
    out = paper._fmt_refs([])
    assert "NAO invente" in out or "lacuna" in out.lower()


def test_fmt_refs_numbered(paper):
    refs = [
        {"authors": "Bond CS", "title": "TcTR crystal structure",
         "year": "1999", "url": "https://doi.org/10.x"},
        {"authors": "Fairlamb AH", "title": "Trypanothione metabolism",
         "year": "1992", "url": "https://doi.org/10.y"},
    ]
    out = paper._fmt_refs(refs)
    assert "[1]" in out and "[2]" in out
    assert "TcTR crystal structure" in out
    assert "10.x" in out


def test_section_enum_matches_canonical(paper):
    tool = next(t for t in paper.get_tools() if t["name"] == "paper_section")
    enum = tool["inputSchema"]["properties"]["section"]["enum"]
    assert "introducao" in enum and "metodos" in enum and "abstract" in enum
