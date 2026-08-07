"""
tests/test_scholaragent.py — Testes da lógica pura do pipeline (sem deps pesadas).
Cobre dedup, crawler, chunking IMRAD, DOI, heurística de metadados, cosseno,
classificação, prompts, RAG (com fakes) e a ponte RAG -> gate.
"""
from datetime import datetime
from pathlib import Path

from scholaragent.scanner.crawler import scan_directories, PaperFile
from scholaragent.scanner.deduplicator import deduplicate
from scholaragent.extractor.pdf_parser import extract_doi, ExtractedPaper
from scholaragent.extractor.metadata_resolver import apply_heuristics
from scholaragent.extractor.section_splitter import split_into_chunks
from scholaragent.brain.classifier import cosine, ThemeClassifier
from scholaragent.chat.prompts import build_prompt
from scholaragent.chat.rag_chain import ScholarRAG
from scholaragent.verify.bridge import evidence_from_rag


# ------------------------------ scanner ----------------------------------- #
def test_crawler_filters_small_and_non_pdf(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 11000)   # > 10KB
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")                    # minúsculo
    (tmp_path / "c.txt").write_text("nao e pdf")
    found = scan_directories([str(tmp_path)])
    assert len(found) == 1
    assert found[0].path.name == "a.pdf"
    assert len(found[0].md5) == 32


def test_dedup_keeps_most_recent():
    old = PaperFile(Path("old.pdf"), "HASH", 1000, datetime(2020, 1, 1))
    new = PaperFile(Path("new.pdf"), "HASH", 1000, datetime(2024, 1, 1))
    other = PaperFile(Path("x.pdf"), "OTHER", 1000, datetime(2022, 1, 1))
    out = deduplicate([old, new, other])
    kept = {p.md5: p for p in out}
    assert len(out) == 2
    assert kept["HASH"].path.name == "new.pdf"


# ------------------------------ extractor --------------------------------- #
def test_extract_doi():
    assert extract_doi("doi:10.1234/abcd.efgh resto") == "10.1234/abcd.efgh"
    assert extract_doi("sem doi aqui") == ""


def test_metadata_heuristics():
    p = ExtractedPaper(
        path=Path("x.pdf"), md5="m1",
        full_text="Titulo. Publicado em 2021 pela revista. Abstract Este estudo avalia o calor.",
    )
    apply_heuristics(p)
    assert p.year == 2021
    assert "estudo" in p.abstract.lower()


def test_section_splitter_imrad():
    text = (
        "Cabecalho do artigo.\n"
        "Abstract\n" + ("Este resumo descreve o estudo em detalhe. " * 6) + "\n"
        "Methods\n" + ("Os metodos incluiram extracao e PCR quantitativa. " * 6) + "\n"
        "Results\n" + ("Os resultados mostraram diferenca significativa. " * 6) + "\n"
    )
    chunks = split_into_chunks("md5x", text)
    sections = {c.section for c in chunks}
    assert {"abstract", "methods", "results"} <= sections


def test_section_splitter_fallback():
    text = "Um texto corrido sem cabecalhos de secao reconheciveis. " * 10
    chunks = split_into_chunks("md5y", text)
    assert chunks and all(c.section == "text" for c in chunks)


def test_section_splitter_excludes_references():
    text = (
        "Cabecalho.\n"
        "Abstract\n" + ("Resumo do estudo em detalhe suficiente. " * 6) + "\n"
        "Methods\n" + ("Metodos de PCR e extracao aplicados. " * 6) + "\n"
        "Results\n" + ("Resultados com diferenca observada. " * 6) + "\n"
        "References\n" + ("Smith J 2020 Journal of Stuff pages. " * 6) + "\n"
    )
    sections = {c.section for c in split_into_chunks("md5z", text)}
    assert "references" not in sections
    assert {"abstract", "methods", "results"} <= sections


# ------------------------------- brain ------------------------------------ #
def test_cosine():
    assert cosine([1, 0, 0], [1, 0, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0


def test_classifier_picks_theme():
    class FakeEmb:
        def embed_query(self, text):
            t = text.lower()
            return [1.0, 0.0] if ("gwas" in t or "nelore" in t) else [0.0, 1.0]

    clf = ThemeClassifier(FakeEmb())
    assert clf.classify("Estudo de GWAS em Nelore", top_n=1) == ["nelore_gwas_eqtl"]
    assert clf.classify("") == ["outros"]


# -------------------------------- chat ------------------------------------ #
def test_build_prompt():
    pr = build_prompt("Quais SNPs?", ["trecho sobre SNP"],
                      [{"authors": "Silva, J; Souza, M", "year": "2024"}])
    assert "Quais SNPs?" in pr and "trecho sobre SNP" in pr and "[1]" in pr


class _FakeEmbedder:
    def embed_query(self, q):
        return [0.1, 0.2, 0.3]


def test_rag_chain_with_fakes():
    class FakeStore:
        def query(self, q, n_results=8, where=None):
            return {
                "documents": [["chunk sobre eQTL no Nelore"]],
                "metadatas": [[{"authors": "Silva, J", "year": "2024",
                                "title": "eQTL Nelore", "paper_md5": "m1"}]],
                "distances": [[0.1]],
            }

    rag = ScholarRAG(FakeStore(), _FakeEmbedder(),
                     ollama_fn=lambda p: "Resposta baseada em [1].")
    res = rag.ask("eQTL?")
    assert "[1]" in res["answer"]
    assert len(res["refs"]) == 1
    assert res["chunks"] == ["chunk sobre eQTL no Nelore"]
    assert res["metas"][0]["paper_md5"] == "m1"


def test_rag_chain_empty():
    class EmptyStore:
        def query(self, q, n_results=8, where=None):
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    rag = ScholarRAG(EmptyStore(), _FakeEmbedder(), ollama_fn=lambda p: "x")
    res = rag.ask("nada")
    assert res["refs"] == [] and res["chunks"] == []


# ------------------------ ponte RAG -> gate ------------------------------- #
def test_evidence_from_rag():
    evs, ref_map = evidence_from_rag(
        ["c1", "c2"],
        [{"paper_md5": "a", "section": "results"}, {"paper_md5": "b", "section": "methods"}],
    )
    assert len(evs) == 2
    assert ref_map[1].text == "c1"
    assert ref_map[2].paper_md5 == "b"
