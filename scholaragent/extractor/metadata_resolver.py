"""
extractor/metadata_resolver.py — Resolve metadados via CrossRef (DOI) com fallback heurístico.
A heurística (apply_heuristics) é pura e testável; a chamada HTTP usa httpx lazy.
"""
from __future__ import annotations
import re

CROSSREF_URL = "https://api.crossref.org/works/{doi}"
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")   # ano completo (corrige grupo capturante)


async def resolve_metadata(paper, email: str = ""):
    """Tenta CrossRef pelo DOI (Polite Pool com email); senão, heurística no texto."""
    if paper.doi:
        try:
            import httpx  # lazy
            async with httpx.AsyncClient(timeout=10) as client:
                params = {"mailto": email} if email else {}
                r = await client.get(CROSSREF_URL.format(doi=paper.doi), params=params)
                if r.status_code == 200:
                    _apply_crossref(paper, r.json().get("message", {}))
        except Exception:
            pass  # fallback silencioso
    return apply_heuristics(paper)


def apply_heuristics(paper):
    """Preenche ano e abstract a partir do texto, quando ausentes."""
    if not paper.year:
        years = YEAR_PATTERN.findall(paper.full_text[:2000])
        paper.year = int(years[0]) if years else None
    if not paper.abstract and paper.full_text:
        low = paper.full_text.lower()
        idx = low.find("abstract")
        if idx != -1:
            paper.abstract = paper.full_text[idx + 8:idx + 800].strip()
        else:
            paper.abstract = paper.full_text[:500].strip()
    return paper


def _apply_crossref(paper, data: dict):
    titles = data.get("title", [])
    if titles:
        paper.title = titles[0]
    paper.authors = [
        f"{a.get('family', '')}, {a.get('given', '')}" for a in data.get("author", [])
    ]
    issued = data.get("issued", {}).get("date-parts", [[]])
    if issued and issued[0]:
        paper.year = issued[0][0]
    container = data.get("container-title", [])
    if container:
        paper.journal = container[0]
    abstract = data.get("abstract", "")
    if abstract:
        paper.abstract = re.sub(r"<[^>]+>", "", abstract).strip()   # remove tags JATS
