"""
extractor/pdf_parser.py — Extrai texto e metadados de PDFs (PyMuPDF, import lazy).
Tenta capturar o DOI no início do texto para resolução via CrossRef.
"""
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)


@dataclass
class ExtractedPaper:
    path: Path
    md5: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    full_text: str = ""
    n_pages: int = 0


def extract_pdf(paper_file) -> ExtractedPaper:
    """Extrai texto completo e tenta capturar metadados básicos."""
    import fitz  # PyMuPDF (lazy)
    doc = fitz.open(str(paper_file.path))
    try:                                  # fecha o handle nativo (evita vazamento)
        full_text = "\n".join(page.get_text() for page in doc)
        meta = doc.metadata or {}
        n_pages = len(doc)
    finally:
        doc.close()
    return ExtractedPaper(
        path=paper_file.path,
        md5=paper_file.md5,
        title=(meta.get("title") or "").strip(),
        doi=extract_doi(full_text[:3000]),
        full_text=full_text,
        n_pages=n_pages,
    )


def extract_doi(text: str) -> str:
    """Captura o primeiro DOI bem-formado do texto (pura — testável)."""
    m = DOI_PATTERN.search(text)
    return m.group(0).rstrip(".,;)") if m else ""
