"""shared/research_sources.py — Fontes de pesquisa externa do LILO.

V10.4 (2026-05-31). Pedido por Dione: dar ao LILO acesso a pesquisas
externas como o Claude (ClinicalTrials, Open Targets, NPI, PubMed, etc.).

Todas as fontes aqui são APIs PÚBLICAS e NÃO exigem credencial:

  * pubmed            -> NCBI E-utilities (eutils)            [chave opcional]
  * europepmc         -> Europe PMC REST (PubMed + preprints + patentes)
  * openalex          -> OpenAlex (250M+ works; substituto do Google Scholar)
  * crossref          -> Crossref REST API
  * semanticscholar   -> Semantic Scholar Graph API           [429 sem chave]
  * googlebooks       -> Google Books API v1 (livros)
  * wikipedia         -> MediaWiki API (conhecimento geral; LILO_WIKI_LANG)
  * clinicaltrials    -> ClinicalTrials.gov API v2
  * opentargets       -> Open Targets Platform GraphQL v4
  * npi               -> NPPES NPI Registry API v2.1

Nota: o Google Scholar NÃO tem API pública e bloqueia scraping (captcha/IP
ban); OpenAlex é o substituto programático recomendado (mesma cobertura).

Cada função `search_<fonte>(query, max_results)` devolve uma lista de dicts
PADRONIZADOS para o ScholarAgent/MCP consumirem:

    {
      "source": "clinicaltrials",
      "title":  "...",
      "url":    "https://...",
      "snippet":"...",          # resumo curto
      "authors":"A; B; C",      # string (pode ser vazia)
      "year":   "2024",         # string (pode ser vazia)
      "id":     "NCT0...",      # id nativo da fonte
    }

`search_all(query, sources=None, max_results=5)` agrega várias fontes.

Boas práticas embutidas: User-Agent identificável, timeouts curtos, retry
com backoff em 429/5xx, e degradação graciosa (uma fonte que falhar NUNCA
derruba as outras — retorna lista vazia + log).

Variáveis de ambiente OPCIONAIS (melhoram rate limit, não obrigatórias):
    NCBI_API_KEY     -> eleva o limite do PubMed de 3 p/ 10 req/s.
    LILO_RESEARCH_EMAIL -> e-mail de contato (etiqueta polida em PubMed/Crossref).
    SEMANTIC_SCHOLAR_API_KEY -> remove o 429 do Semantic Scholar.
"""

import os
import time
from urllib.parse import quote_plus

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from .logger import get_logger
    log = get_logger("ResearchSources")
except Exception:  # uso standalone
    import logging
    log = logging.getLogger("ResearchSources")

TIMEOUT = float(os.getenv("LILO_RESEARCH_TIMEOUT", "15"))
_EMAIL = os.getenv("LILO_RESEARCH_EMAIL", "lilo@localhost")
_UA = "LILO/1.0 (research; %s)" % _EMAIL
_NCBI_KEY = os.getenv("NCBI_API_KEY", "").strip()
_S2_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
_GBOOKS_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()

SOURCES = ("pubmed", "europepmc", "openalex", "crossref", "semanticscholar",
           "googlebooks", "wikipedia", "clinicaltrials", "opentargets", "npi")


# ── HTTP helpers (com retry/backoff) ─────────────────────────────────────────
def _req(method, url, *, params=None, json_body=None, headers=None,
         retries=2):
    """GET/POST JSON com retry exponencial em 429/5xx. Devolve dict|list|None."""
    if requests is None:
        log.warning("pacote 'requests' ausente; fontes externas indisponiveis")
        return None
    h = {"User-Agent": _UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, params=params, json=json_body,
                                 headers=h, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504):
                last = "HTTP %d" % r.status_code
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                log.warning("%s -> %s (apos retries)", url, last)
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = str(e)
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            log.warning("falha em %s: %s", url, last)
            return None
    return None


def _std(source, title, url, snippet="", authors="", year="", id="", doi=""):
    # DOI normalizado (sem prefixo de URL) -> campo estruturado p/ o scholar/citacoes.
    d = (doi or "").strip()
    _low = d.lower()
    for _pfx in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if _low.startswith(_pfx):
            d = d[len(_pfx):]
            break
    return {"source": source, "title": (title or "").strip(),
            "url": url or "", "snippet": (snippet or "").strip()[:500],
            "authors": authors or "", "year": str(year or ""),
            "id": str(id or ""), "doi": d.strip()}


def _openalex_abstract(inv):
    """Reconstrói o abstract do OpenAlex (vem como inverted index posicional)."""
    if not isinstance(inv, dict):
        return ""
    try:
        words = sorted((pos, w) for w, ps in inv.items() for pos in (ps or []))
        return " ".join(w for _, w in words)
    except Exception:
        return ""


# ── PubMed (NCBI E-utilities) ────────────────────────────────────────────────
def search_pubmed(query, max_results=5):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    common = {"db": "pubmed"}
    if _NCBI_KEY:
        common["api_key"] = _NCBI_KEY
    if _EMAIL:
        common["email"] = _EMAIL
    es = _req("GET", base + "/esearch.fcgi",
              params={**common, "term": query, "retmax": max_results,
                      "retmode": "json"})
    if not es:
        return []
    ids = (es.get("esearchresult", {}) or {}).get("idlist", []) or []
    if not ids:
        return []
    summ = _req("GET", base + "/esummary.fcgi",
                params={**common, "id": ",".join(ids), "retmode": "json"})
    out = []
    res = (summ or {}).get("result", {}) or {}
    for uid in ids:
        it = res.get(uid)
        if not it:
            continue
        authors = "; ".join(a.get("name", "") for a in it.get("authors", [])[:6])
        _doi = next((a.get("value", "") for a in (it.get("articleids", []) or [])
                     if (a.get("idtype") or "").lower() == "doi"), "")
        out.append(_std("pubmed", it.get("title", ""),
                        "https://pubmed.ncbi.nlm.nih.gov/%s/" % uid,
                        snippet=it.get("source", "") + " " + it.get("pubdate", ""),
                        authors=authors, year=(it.get("pubdate", "")[:4]),
                        id=uid, doi=_doi))
    return out


# ── ClinicalTrials.gov API v2 ────────────────────────────────────────────────
def search_clinicaltrials(query, max_results=5):
    url = "https://clinicaltrials.gov/api/v2/studies"
    data = _req("GET", url, params={"query.term": query,
                                    "pageSize": max_results, "format": "json"})
    if not data:
        return []
    out = []
    for st in (data.get("studies", []) or [])[:max_results]:
        ps = st.get("protocolSection", {}) or {}
        idm = ps.get("identificationModule", {}) or {}
        desc = ps.get("descriptionModule", {}) or {}
        status = (ps.get("statusModule", {}) or {}).get("overallStatus", "")
        nct = idm.get("nctId", "")
        out.append(_std("clinicaltrials", idm.get("briefTitle", ""),
                        "https://clinicaltrials.gov/study/%s" % nct,
                        snippet="[%s] %s" % (status, desc.get("briefSummary", "")),
                        year=(ps.get("statusModule", {}) or {})
                              .get("startDateStruct", {}).get("date", "")[:4],
                        id=nct))
    return out


# ── Open Targets Platform (GraphQL v4) ───────────────────────────────────────
def search_opentargets(query, max_results=5):
    url = "https://api.platform.opentargets.org/api/v4/graphql"
    gql = ("query($q:String!,$n:Int!){search(queryString:$q,"
           "entityNames:[\"target\",\"disease\",\"drug\"],"
           "page:{index:0,size:$n}){hits{id name entity "
           "description object{__typename}}}}")
    data = _req("POST", url,
                json_body={"query": gql,
                           "variables": {"q": query, "n": max_results}},
                headers={"Content-Type": "application/json"})
    if not data:
        return []
    hits = (((data.get("data") or {}).get("search") or {}).get("hits") or [])
    out = []
    for h in hits[:max_results]:
        ent = h.get("entity", "")
        hid = h.get("id", "")
        urlmap = {"target": "https://platform.opentargets.org/target/%s",
                  "disease": "https://platform.opentargets.org/disease/%s",
                  "drug": "https://platform.opentargets.org/drug/%s"}
        out.append(_std("opentargets", "%s (%s)" % (h.get("name", ""), ent),
                        (urlmap.get(ent, "https://platform.opentargets.org/%s")
                         % hid),
                        snippet=h.get("description", "") or ent,
                        id=hid))
    return out


# ── NPI Registry (NPPES) ─────────────────────────────────────────────────────
def search_npi(query, max_results=5):
    url = "https://npiregistry.cms.hhs.gov/api/"
    # Heurística: trata a query como nome de organização OU sobrenome.
    params = {"version": "2.1", "limit": max_results,
              "organization_name": "*%s*" % query}
    data = _req("GET", url, params=params)
    if not data or not (data.get("results")):
        params = {"version": "2.1", "limit": max_results, "last_name": query}
        data = _req("GET", url, params=params)
    out = []
    for r in (data or {}).get("results", [])[:max_results]:
        basic = r.get("basic", {}) or {}
        name = basic.get("organization_name") or " ".join(
            x for x in [basic.get("first_name"), basic.get("last_name")] if x)
        addr = (r.get("addresses", [{}]) or [{}])[0]
        taxon = (r.get("taxonomies", [{}]) or [{}])[0].get("desc", "")
        out.append(_std("npi", name or "NPI %s" % r.get("number", ""),
                        "https://npiregistry.cms.hhs.gov/provider-view/%s"
                        % r.get("number", ""),
                        snippet="%s | %s, %s" % (taxon, addr.get("city", ""),
                                                 addr.get("state", "")),
                        id=r.get("number", "")))
    return out


# ── Crossref ─────────────────────────────────────────────────────────────────
def search_crossref(query, max_results=5):
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": max_results}
    if _EMAIL:
        params["mailto"] = _EMAIL
    data = _req("GET", url, params=params)
    if not data:
        return []
    out = []
    for it in ((data.get("message", {}) or {}).get("items", []) or [])[:max_results]:
        title = (it.get("title") or [""])[0]
        authors = "; ".join(
            ("%s %s" % (a.get("given", ""), a.get("family", ""))).strip()
            for a in (it.get("author", []) or [])[:6])
        yr = ""
        try:
            yr = str(it.get("issued", {}).get("date-parts", [[None]])[0][0] or "")
        except Exception:
            yr = ""
        out.append(_std("crossref", title,
                        it.get("URL", "https://doi.org/%s" % it.get("DOI", "")),
                        snippet="%s (%s)" % (it.get("container-title", [""])[0]
                                             if it.get("container-title") else "",
                                             it.get("type", "")),
                        authors=authors, year=yr, id=it.get("DOI", ""),
                        doi=it.get("DOI", "")))
    return out


# ── Semantic Scholar ─────────────────────────────────────────────────────────
def search_semanticscholar(query, max_results=5):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {"x-api-key": _S2_KEY} if _S2_KEY else None
    data = _req("GET", url, params={"query": query, "limit": max_results,
                "fields": "title,abstract,year,authors,url,externalIds"},
                headers=headers, retries=3)
    if not data:
        return []
    out = []
    for p in (data.get("data", []) or [])[:max_results]:
        authors = "; ".join(a.get("name", "") for a in (p.get("authors", []) or [])[:6])
        doi = (p.get("externalIds", {}) or {}).get("DOI", "")
        out.append(_std("semanticscholar", p.get("title", ""),
                        p.get("url", "") or ("https://doi.org/%s" % doi if doi else ""),
                        snippet=p.get("abstract", "") or "",
                        authors=authors, year=p.get("year", ""),
                        id=p.get("paperId", ""), doi=doi))
    return out


# ── OpenAlex (substituto programático do Google Scholar) ─────────────────────
def search_openalex(query, max_results=5):
    """OpenAlex: 250M+ trabalhos acadêmicos, API gratuita SEM chave. É o
    substituto correto do Google Scholar (que não tem API e bloqueia scraping).
    """
    url = "https://api.openalex.org/works"
    params = {"search": query, "per-page": max_results}
    if _EMAIL:
        params["mailto"] = _EMAIL  # "polite pool" do OpenAlex
    data = _req("GET", url, params=params)
    if not data:
        return []
    out = []
    for w in (data.get("results", []) or [])[:max_results]:
        authors = "; ".join(
            ((a.get("author", {}) or {}).get("display_name", ""))
            for a in (w.get("authorships", []) or [])[:6])
        doi = w.get("doi") or ""
        out.append(_std(
            "openalex", w.get("title", "") or w.get("display_name", ""),
            doi or w.get("id", ""),
            snippet=_openalex_abstract(w.get("abstract_inverted_index")),
            authors=authors, year=w.get("publication_year", ""),
            id=w.get("id", ""), doi=doi))
    return out


# ── Europe PMC (PubMed + preprints + patentes + texto completo) ──────────────
def search_europepmc(query, max_results=5):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    data = _req("GET", url, params={"query": query, "format": "json",
                                    "pageSize": max_results, "resultType": "lite"})
    if not data:
        return []
    out = []
    for r in ((data.get("resultList", {}) or {}).get("result", []) or [])[:max_results]:
        src, ext = r.get("source", ""), r.get("id", "")
        doi = r.get("doi", "")
        link = ("https://europepmc.org/article/%s/%s" % (src, ext)) if (src and ext) \
            else (("https://doi.org/%s" % doi) if doi else "")
        out.append(_std("europepmc", r.get("title", ""), link,
                        snippet="%s %s" % (r.get("journalTitle", ""),
                                           r.get("pubYear", "")),
                        authors=r.get("authorString", ""),
                        year=r.get("pubYear", ""), id=ext or doi, doi=doi))
    return out


# ── Google Books (API oficial v1) ───────────────────────────────────────────
def search_googlebooks(query, max_results=5):
    """Google Books API v1. SEM chave a quota anônima é compartilhada por IP e
    satura facilmente (HTTP 429 -> [] por degradação graciosa). Defina
    GOOGLE_BOOKS_API_KEY (gratuita, ~1000 req/dia) para uso confiável.
    """
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": min(max_results, 40), "country": "BR"}
    if _GBOOKS_KEY:
        params["key"] = _GBOOKS_KEY
    data = _req("GET", url, params=params)
    if not data:
        return []
    out = []
    for v in (data.get("items", []) or [])[:max_results]:
        vi = v.get("volumeInfo", {}) or {}
        authors = "; ".join(vi.get("authors", []) or [])
        snippet = (vi.get("description", "") or "") or (
            "%s %s" % (vi.get("publisher", ""), vi.get("publishedDate", "")))
        out.append(_std("googlebooks", vi.get("title", ""),
                        vi.get("infoLink", "") or vi.get("canonicalVolumeLink", ""),
                        snippet=snippet, authors=authors,
                        year=(vi.get("publishedDate", "") or "")[:4],
                        id=v.get("id", "")))
    return out


# ── Wikipedia (conhecimento geral; idioma via LILO_WIKI_LANG) ────────────────
def search_wikipedia(query, max_results=5):
    import re as _re
    lang = os.getenv("LILO_WIKI_LANG", "pt")
    url = "https://%s.wikipedia.org/w/api.php" % lang
    data = _req("GET", url, params={"action": "query", "list": "search",
                "srsearch": query, "srlimit": max_results, "format": "json",
                "srprop": "snippet"})
    if not data:
        return []
    out = []
    for r in (((data.get("query") or {}).get("search")) or [])[:max_results]:
        title = r.get("title", "")
        snip = _re.sub(r"<[^>]+>", "", r.get("snippet", "") or "")
        out.append(_std("wikipedia", title,
                        "https://%s.wikipedia.org/wiki/%s"
                        % (lang, quote_plus(title.replace(" ", "_"))),
                        snippet=snip, id=str(r.get("pageid", ""))))
    return out


_DISPATCH = {
    "pubmed": search_pubmed,
    "europepmc": search_europepmc,
    "openalex": search_openalex,
    "crossref": search_crossref,
    "semanticscholar": search_semanticscholar,
    "googlebooks": search_googlebooks,
    "wikipedia": search_wikipedia,
    "clinicaltrials": search_clinicaltrials,
    "opentargets": search_opentargets,
    "npi": search_npi,
}


def search_all(query, sources=None, max_results=5):
    """Agrega resultados de várias fontes. `sources`=None => todas.

    Retorna {"query":..., "results":[...], "by_source":{src:n}, "errors":[...]}.
    Cada fonte é isolada: falha em uma não impede as demais.
    """
    sources = list(sources) if sources else list(SOURCES)
    results, by_source, errors = [], {}, []
    for src in sources:
        fn = _DISPATCH.get(src)
        if not fn:
            errors.append("fonte desconhecida: %s" % src)
            continue
        try:
            r = fn(query, max_results) or []
            results.extend(r)
            by_source[src] = len(r)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (src, e))
            by_source[src] = 0
            log.warning("fonte %s falhou: %s", src, e)
    return {"query": query, "results": results,
            "by_source": by_source, "errors": errors}


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "dengue"
    srcs = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    res = search_all(q, srcs, max_results=2)
    print("query=%s  by_source=%s  errors=%s" %
          (res["query"], res["by_source"], res["errors"]))
    for r in res["results"]:
        print("  [%s] %s -> %s" % (r["source"], r["title"][:70], r["url"]))
