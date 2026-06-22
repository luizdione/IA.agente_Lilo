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
    title_guess: str = ""   # melhor palpite de título (maior fonte da pág. 1)


def extract_pdf(paper_file) -> ExtractedPaper:
    """Extrai texto completo e tenta capturar metadados básicos."""
    import fitz  # PyMuPDF (lazy)
    doc = fitz.open(str(paper_file.path))
    try:                                  # fecha o handle nativo (evita vazamento)
        full_text = "\n".join(page.get_text() for page in doc)
        meta = doc.metadata or {}
        n_pages = len(doc)
        title_guess = _title_from_fonts(doc[0]) if n_pages else ""
    finally:
        doc.close()
    return ExtractedPaper(
        path=paper_file.path,
        md5=paper_file.md5,
        title=(meta.get("title") or "").strip(),
        doi=extract_doi(full_text[:3000]),
        full_text=full_text,
        n_pages=n_pages,
        title_guess=title_guess,
    )


def _title_from_fonts(page) -> str:
    """Maior fonte na metade superior da página 1 — costuma ser o título."""
    try:
        data = page.get_text("dict")
        h = page.rect.height or 1000
    except Exception:
        return ""
    spans = []
    for blk in data.get("blocks", []):
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                txt = (sp.get("text") or "").strip()
                y = sp.get("bbox", [0, 0, 0, 0])[1]
                if txt and len(txt) >= 3 and y < h * 0.5:
                    spans.append((round(sp.get("size", 0.0), 1), y, txt))
    if not spans:
        return ""
    top = max(s[0] for s in spans)
    parts = sorted((s for s in spans if s[0] >= top - 0.5), key=lambda s: s[1])
    return " ".join(t for _, _, t in parts).strip()[:300]


def extract_doi(text: str) -> str:
    """Captura o primeiro DOI bem-formado do texto (pura — testável)."""
    m = DOI_PATTERN.search(text)
    return m.group(0).rstrip(".,;)") if m else ""
