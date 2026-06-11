"""
shared/web_search.py -- Busca web para todos os subagentes LILO
================================================================
Permite que qualquer subagente busque conteudo na internet.

Usa DuckDuckGo (sem API key) como motor de busca principal,
com fallback para scraping direto de paginas.

Uso:
    from shared.web_search import web_search, fetch_page

    results = web_search("CRISPR Trypanosoma cruzi 2024")
    content = fetch_page("https://pubmed.ncbi.nlm.nih.gov/12345/")
"""

import re
import json
import time
from typing import Optional
from urllib.parse import quote_plus

try:
    import requests
except ImportError:
    requests = None

from .logger import get_logger

log = get_logger("WebSearch")

# Sites confiaveis para conteudo cientifico
TRUSTED_DOMAINS = [
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "arxiv.org",
    "doi.org",
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "cell.com",
    "plos.org",
    "biorxiv.org",
    "medrxiv.org",
    "frontiersin.org",
    "mdpi.com",
    "academic.oup.com",
    "bmj.com",
    "thelancet.com",
    "nejm.org",
    "wikipedia.org",
    "uniprot.org",
    "rcsb.org",
    "ensembl.org",
    "ncbi.nlm.nih.gov",
    "ebi.ac.uk",
    "bioconductor.org",
    "python.org",
    "docs.python.org",
    "pypi.org",
    "github.com",
    "stackoverflow.com",
    "medium.com",
    "researchgate.net",
    "semanticscholar.org",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT = 15


def _is_trusted(url: str) -> bool:
    """Verifica se URL pertence a um dominio confiavel."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in TRUSTED_DOMAINS)


def web_search(
    query: str,
    max_results: int = 5,
    trusted_only: bool = True,
    region: str = "br-pt",
) -> list[dict]:
    """
    Busca na web via DuckDuckGo (sem API key).

    Args:
        query: termos de busca
        max_results: maximo de resultados (default 5)
        trusted_only: filtrar apenas dominios confiaveis
        region: regiao de busca (default br-pt)

    Returns:
        Lista de dicts com title, url, snippet
    """
    results = []

    # Metodo 1: DuckDuckGo HTML (sem dependencia extra)
    try:
        results = _search_ddg_html(query, max_results * 2)
        log.info(f"DuckDuckGo HTML: {len(results)} resultados")
    except Exception as e:
        log.warning(f"DuckDuckGo HTML falhou: {e}")

    # Metodo 2: DuckDuckGo API lite
    if not results:
        try:
            results = _search_ddg_lite(query, max_results * 2)
            log.info(f"DuckDuckGo Lite: {len(results)} resultados")
        except Exception as e:
            log.warning(f"DuckDuckGo Lite falhou: {e}")

    # Metodo 3: duckduckgo-search (se instalado)
    if not results:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=region, max_results=max_results * 2):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", r.get("link", "")),
                        "snippet": r.get("body", r.get("snippet", "")),
                    })
            log.info(f"duckduckgo-search: {len(results)} resultados")
        except ImportError:
            log.debug("duckduckgo-search nao instalado")
        except Exception as e:
            log.warning(f"duckduckgo-search falhou: {e}")

    # Filtrar por dominios confiaveis
    if trusted_only and results:
        trusted = [r for r in results if _is_trusted(r.get("url", ""))]
        if trusted:
            results = trusted
        else:
            log.info("Nenhum resultado em dominio confiavel, retornando todos")

    return results[:max_results]


def _search_ddg_html(query: str, max_results: int = 10) -> list[dict]:
    """Busca DuckDuckGo via HTML scraping."""
    if not requests:
        return []

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()

    results = []
    # Parse simples do HTML (sem BeautifulSoup)
    # Cada resultado esta em <a class="result__a" href="...">
    pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
    snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'

    links = re.findall(pattern, r.text, re.DOTALL)
    snippets = re.findall(snippet_pattern, r.text, re.DOTALL)

    for i, (href, title) in enumerate(links[:max_results]):
        # Limpar HTML tags do titulo
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        clean_snippet = ""
        if i < len(snippets):
            clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

        # DuckDuckGo redireciona - extrair URL real
        real_url = href
        if "uddg=" in href:
            m = re.search(r'uddg=([^&]+)', href)
            if m:
                from urllib.parse import unquote
                real_url = unquote(m.group(1))

        if clean_title and real_url:
            results.append({
                "title": clean_title,
                "url": real_url,
                "snippet": clean_snippet,
            })

    return results


def _search_ddg_lite(query: str, max_results: int = 10) -> list[dict]:
    """Busca DuckDuckGo via API lite."""
    if not requests:
        return []

    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()

    results = []
    # Extrair links da pagina lite
    pattern = r'<a[^>]*href="(https?://[^"]+)"[^>]*class="[^"]*result-link[^"]*"[^>]*>(.*?)</a>'
    for href, title in re.findall(pattern, r.text, re.DOTALL)[:max_results]:
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        if clean_title:
            results.append({
                "title": clean_title,
                "url": href,
                "snippet": "",
            })

    return results


def fetch_page(
    url: str,
    max_chars: int = 5000,
    timeout: int = TIMEOUT,
) -> str:
    """
    Busca e extrai texto de uma pagina web.

    Args:
        url: URL da pagina
        max_chars: maximo de caracteres a retornar
        timeout: timeout em segundos

    Returns:
        Texto limpo da pagina (sem HTML).
    """
    if not requests:
        return "[ERRO] requests nao instalado"

    if not _is_trusted(url):
        return f"[AVISO] Dominio nao confiavel: {url}"

    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()

        # Extrair texto (remover tags HTML)
        text = r.text
        # Remover scripts e styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        # Remover tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Limpar espacos
        text = re.sub(r'\s+', ' ', text).strip()
        # Decodificar entidades HTML basicas
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")

        return text[:max_chars]

    except Exception as e:
        return f"[ERRO] Falha ao buscar {url}: {e}"


def search_and_summarize(
    query: str,
    max_results: int = 3,
    max_chars_per_page: int = 2000,
) -> str:
    """
    Busca na web e retorna resumo formatado.
    Util para subagentes que precisam de contexto externo.

    Returns:
        Texto Markdown com resultados e trechos.
    """
    results = web_search(query, max_results=max_results)

    if not results:
        return f"Nenhum resultado encontrado para: {query}"

    lines = [f"## Resultados para: {query}\n"]

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"**URL:** {r['url']}")
        if r.get("snippet"):
            lines.append(f"**Resumo:** {r['snippet']}")

        # Buscar conteudo da pagina
        if _is_trusted(r["url"]):
            content = fetch_page(r["url"], max_chars=max_chars_per_page)
            if not content.startswith("[ERRO]"):
                # Pegar primeiros paragrafos relevantes
                lines.append(f"\n{content[:max_chars_per_page]}")

        lines.append("")

    return "\n".join(lines)
