"""tests/test_docgen.py — DocGenAgent (V13.2), offline (xlsx/pptx, sem LLM)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def docgen():
    from agents.docgen.agent import DocGenAgent
    return DocGenAgent()


def test_tools_and_health(docgen):
    names = {t["name"] for t in docgen.get_tools()}
    assert {"make_report_docx", "make_docx", "make_xlsx", "make_pptx"} <= names
    h = docgen.health()
    assert h["openpyxl"] and h["python_pptx"]


def test_xlsx_generation(docgen, tmp_path):
    out = tmp_path / "t.xlsx"
    rows = [["gene", "valor"], ["HSP70", 2.4], ["TcTR", 1.2]]
    msg = docgen._to_xlsx(rows, out, title="Dados")
    assert out.exists() and out.stat().st_size > 0
    assert "XLSX gerado" in msg


def test_pptx_generation(docgen, tmp_path):
    out = tmp_path / "t.pptx"
    outline = "# Intro\n- a\n- b\n# Metodos\n- docking\n# Resultados\n- IC50"
    msg = docgen._to_pptx(outline, out)
    assert out.exists() and out.stat().st_size > 0
    assert "PPTX gerado" in msg


def test_parse_rows_tsv(docgen):
    rows = docgen._parse_rows({"tsv": "a\tb\n1\t2\n3\t4"})
    assert rows == [["a", "b"], ["1", "2"], ["3", "4"]]


def test_parse_rows_csv(docgen):
    rows = docgen._parse_rows({"csv": "a,b\n1,2"})
    assert rows == [["a", "b"], ["1", "2"]]
