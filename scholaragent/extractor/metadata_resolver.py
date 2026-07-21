"""
extractor/metadata_resolver.py — Resolve metadados via CrossRef com fallback robusto.

Estratégia (httpx lazy; CrossRef polite pool com email):
  1. DOI no texto -> CrossRef por DOI.
  2. Sem título decente -> extrai um título CANDIDATO do texto e consulta o CrossRef
     POR TÍTULO (query.bibliographic), aceitando só se o título retornado bate com o
     candidato (checagem de similaridade) — evita casar com o paper errado.
  3. Heurística final (ano/abstract/título candidato).
"""
from __future__ import annotations
import re

CROSSREF_DOI_URL = "https://api.crossref.org/works/{doi}"
CROSSREF_QUERY_URL = "https://api.crossref.org/works"
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
_TITLE_BAD_HINTS = ("doi", "http", "www.", "@", "issn", "copyright", "©",
                    "vol.", "all rights reserved", "downloaded from")


def _good_title(t: str) -> bool:
    """Título 'decente': comprimento razoável, tem espaços, não é um código/filename."""
    t = (t or "").strip()
    if len(t) < 15 or " " not in t:
        return False
    if t.lower().endswith((".p65", ".pdf", ".doc")):
        return False
    if sum(c.isdigit() for c in t) > len(t) * 0.3:   # muitos dígitos -> código de página
        return False
    return True


def _candidate_title(full_text: str) -> str:
    """Melhor palpite de título a partir das primeiras linhas (para busca no CrossRef)."""
    lines = [ln.strip() for ln in (full_text or "")[:2500].splitlines() if ln.strip()]
    cands = []
    for ln in lines[:25]:
        if not (20 <= len(ln) <= 250) or len(ln.split()) < 3:
            continue
        low = ln.lower()
        if any(b in low for b in _TITLE_BAD_HINTS):
            continue
        if sum(c.isdigit() for c in ln) > len(ln) * 0.25:
            continue
        cands.append(ln)
    return max(cands[:6], key=len) if cands else ""


def _title_tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Zà-úÀ-Ú]{3,}", (s or "").lower())}


def _title_match(candidate: str, found: str) -> bool:
    """Aceita o resultado do CrossRef só se compartilha >=50% dos tokens do candidato."""
    ca, fo = _title_tokens(candidate), _title_tokens(found)
    if not ca or not fo:
        return False
    return len(ca & fo) >= max(3, int(0.5 * len(ca)))


async def resolve_metadata(paper, email: str = ""):
    candidate = (getattr(paper, "title_guess", "") or "").strip() or _candidate_title(paper.full_text)
    try:
        import httpx  # lazy
        params0 = {"mailto": email} if email else {}
        async with httpx.AsyncClient(timeout=12) as client:
            # 1) DOI direto
            if paper.doi:
                try:
                    r = await client.get(CROSSREF_DOI_URL.format(doi=paper.doi), params=params0)
                    if r.status_code == 200:
                        _apply_crossref(paper, r.json().get("message", {}))
                except Exception:
                    pass
            # 2) sem título decente -> busca por título (bibliographic)
            if not _good_title(paper.title) and candidate:
                try:
                    r = await client.get(CROSSREF_QUERY_URL, params={
                        **params0, "query.bibliographic": candidate, "rows": "1"})
                    if r.status_code == 200:
                        items = r.json().get("message", {}).get("items", [])
                        if items:
                            found = items[0]
                            ftitle = (found.get("title") or [""])[0]
                            if _title_match(candidate, ftitle):
                                _apply_crossref(paper, found)
                                if not paper.doi:
                                    paper.doi = found.get("DOI", "") or ""
                except Exception:
                    pass
    except Exception:
        pass  # httpx ausente / rede -> só heurística
    return apply_heuristics(paper, candidate)


def apply_heuristics(paper, candidate_title: str = ""):
    """Preenche título (candidato), ano e abstract quando ainda ausentes."""
    if not _good_title(paper.title) and candidate_title:
        paper.title = candidate_title
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
    if titles and titles[0].strip():
        paper.title = titles[0].strip()
    authors = [
        f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
        for a in data.get("author", [])
    ]
    if authors:
        paper.authors = authors
    issued = data.get("issued", {}).get("date-parts", [[]])
    if issued and issued[0]:
        paper.year = issued[0][0]
    container = data.get("container-title", [])
    if container and container[0].strip():
        paper.journal = container[0].strip()
    abstract = data.get("abstract", "")
    if abstract:
        paper.abstract = re.sub(r"<[^>]+>", "", abstract).strip()   # remove tags JATS
