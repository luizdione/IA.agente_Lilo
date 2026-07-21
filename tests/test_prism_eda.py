"""tests/test_prism_eda.py — modo EDA do PrismAgent (V13.3), offline."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def prism():
    from agents.prism_ai.main import PrismAgent
    return PrismAgent()


def _make_csv(tmp_path):
    import pandas as pd
    fp = tmp_path / "exp.csv"
    pd.DataFrame({
        "gene": ["a", "b", "c", "d", "e", "f"],
        "expr": [2.4, 3.1, 1.2, 5.5, 4.0, 2.2],
        "grupo": ["A", "B", "A", "B", "A", "B"],
        "score": [10, 20, 15, 25, 12, 22],
    }).to_csv(fp, index=False)
    return fp


def test_eda_tool_exposed(prism):
    assert "prism_eda" in {t["name"] for t in prism.get_tools()}


def test_eda_profile_and_figures(prism, tmp_path):
    csv = _make_csv(tmp_path)
    out = tmp_path / "out"
    md = prism._eda(str(csv), str(out), {})
    assert "EDA" in md and "Dimensões" in md
    assert "expr" in md and "score" in md          # describe das numericas
    pngs = list(out.glob("*.png"))
    assert any("corr" in p.name for p in pngs)     # heatmap de correlacao
    assert len(pngs) >= 3                           # 2 hist + 1 corr


def test_eda_routed_via_run_mode(prism, tmp_path):
    csv = _make_csv(tmp_path)
    md = prism.run("eda", {"mode": "eda", "file_path": str(csv),
                           "output_dir": str(tmp_path / "o2")})
    assert "perfil explorat" in md.lower()


def test_eda_bad_file_graceful(prism, tmp_path):
    md = prism._eda(str(tmp_path / "naoexiste.csv"), str(tmp_path / "o3"), {})
    assert "erro" in md.lower()
