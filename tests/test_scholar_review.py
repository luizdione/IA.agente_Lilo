"""tests/test_scholar_review.py — dedup da revisao de literatura (V13.1), offline."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def scholar():
    from agents.scholaragent.agent import ScholarAgent
    return ScholarAgent()


def test_dedup_by_doi(scholar):
    rows = [
        {"title": "A", "id": "https://doi.org/10.1/x"},
        {"title": "A (mirror)", "id": "10.1/x"},          # mesmo DOI
        {"title": "B", "id": "10.2/y"},
    ]
    out = scholar._dedup(rows)
    assert len(out) == 2


def test_dedup_by_title_when_no_doi(scholar):
    rows = [
        {"title": "Trypanothione reductase inhibitors", "id": ""},
        {"title": "Trypanothione   reductase, inhibitors!", "id": ""},  # ~mesmo titulo
        {"title": "Totally different paper", "id": ""},
    ]
    out = scholar._dedup(rows)
    assert len(out) == 2


def test_dedup_preserves_order(scholar):
    rows = [{"title": "First", "id": "10.a/1"},
            {"title": "Second", "id": "10.b/2"}]
    out = scholar._dedup(rows)
    assert [r["title"] for r in out] == ["First", "Second"]


def test_scholar_review_tool_exposed(scholar):
    assert "scholar_review" in {t["name"] for t in scholar.get_tools()}
