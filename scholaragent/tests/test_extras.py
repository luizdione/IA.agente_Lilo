"""
tests/test_extras.py -- Testes do watcher (filtro) e da tabela de evidências.
Pura lógica; sem GPU, sem LLM, sem watchdog instalado.
"""
from pathlib import Path

from scholaragent.scanner.watcher import PaperWatcher
from scholaragent.export.table_builder import build_evidence_table, to_markdown


# ------------------------------ watcher ----------------------------------- #
def test_watcher_accept(tmp_path):
    big = tmp_path / "a.pdf"; big.write_bytes(b"%PDF-1.4\n" + b"0" * 11000)
    small = tmp_path / "b.pdf"; small.write_bytes(b"%PDF")
    txt = tmp_path / "c.txt"; txt.write_text("x")
    w = PaperWatcher([str(tmp_path)], on_pdf=lambda p: None)
    assert w.accept(big) is True
    assert w.accept(small) is False           # < tamanho mínimo
    assert w.accept(txt) is False             # não é PDF
    assert w.accept(tmp_path / "nope.pdf") is False  # inexistente


def test_watcher_handle_calls_callback(tmp_path):
    big = tmp_path / "a.pdf"; big.write_bytes(b"%PDF-1.4\n" + b"0" * 11000)
    seen = []
    w = PaperWatcher([str(tmp_path)], on_pdf=seen.append)
    assert w.handle(big) is True
    assert len(seen) == 1 and isinstance(seen[0], Path)
    assert w.handle(tmp_path / "c.txt") is False
    assert len(seen) == 1                      # rejeitado não dispara


# -------------------------- tabela de evidências -------------------------- #
def test_evidence_table_rows():
    chunks = ["O   eQTL   regula   a   expressao."]
    metas = [{"authors": "Silva, J; Souza, M", "year": "2024",
              "journal": "Gene", "doi": "10.1/x", "section": "results"}]
    rows = build_evidence_table(chunks, metas, snippet_chars=50)
    r = rows[0]
    assert len(rows) == 1 and r["ref"] == 1
    assert r["autor"] == "Silva, J" and r["ano"] == "2024"
    assert r["periodico"] == "Gene" and r["doi"] == "10.1/x" and r["secao"] == "results"
    assert "  " not in r["trecho"]             # espaços normalizados


def test_evidence_table_markdown():
    rows = build_evidence_table(["trecho a"], [{"authors": "X, Y", "year": "2020"}])
    md = to_markdown(rows)
    assert md.startswith("| #") and "X, Y" in md and "2020" in md
    assert to_markdown([]) == "_(nenhuma evidencia)_"
