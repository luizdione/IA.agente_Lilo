"""
reference_formatter.py
Busca formatação de referências por ISSN via CrossRef API e formata citações.
"""

import requests
import re
import json
from typing import Optional


# Cache simples em memória para estilos já consultados
_style_cache: dict[str, dict] = {}


def lookup_journal_by_issn(issn: str) -> dict:
    """
    Consulta CrossRef API para obter informações da revista pelo ISSN.
    Retorna: {title, publisher, issn, subjects, csl_style_hint}
    """
    issn = issn.strip().upper()
    if not re.match(r"^\d{4}-?\d{3}[\dX]$", issn):
        raise ValueError(f"ISSN inválido: {issn}")

    # Normalizar com hífen
    if "-" not in issn:
        issn = f"{issn[:4]}-{issn[4:]}"

    if issn in _style_cache:
        return _style_cache[issn]

    # CrossRef journal endpoint
    url = f"https://api.crossref.org/journals/{issn}"
    headers = {
        "User-Agent": "ScholarAgent/1.0 (mailto:scholar-agent@example.com)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get("message", {})
            result = {
                "title": data.get("title", "Desconhecido"),
                "publisher": data.get("publisher", ""),
                "issn": issn,
                "subjects": [s.get("name", "") for s in data.get("subjects", [])],
                "counts": data.get("counts", {}),
            }
            _style_cache[issn] = result
            return result
        elif resp.status_code == 404:
            raise ValueError(f"ISSN {issn} não encontrado no CrossRef.")
        else:
            raise RuntimeError(f"CrossRef retornou status {resp.status_code}")
    except requests.ConnectionError:
        raise RuntimeError("Sem conexão com CrossRef API.")


def fetch_sample_references(issn: str, n: int = 3) -> list[dict]:
    """
    Busca artigos recentes da revista no CrossRef para extrair padrão de formatação.
    Retorna metadados crus de n artigos.
    """
    issn = issn.strip()
    if "-" not in issn:
        issn = f"{issn[:4]}-{issn[4:]}"

    url = "https://api.crossref.org/works"
    params = {
        "filter": f"issn:{issn}",
        "rows": n,
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,author,published-print,published-online,volume,issue,page,container-title",
    }
    headers = {
        "User-Agent": "ScholarAgent/1.0 (mailto:scholar-agent@example.com)"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        return items
    except Exception as e:
        raise RuntimeError(f"Erro ao buscar artigos de amostra: {e}")


def build_reference_prompt(issn: str, raw_references: str) -> str:
    """
    Constrói o prompt para o LLM formatar as referências no estilo da revista.
    Busca exemplos reais no CrossRef para dar contexto ao modelo.
    """
    # Info da revista
    try:
        journal_info = lookup_journal_by_issn(issn)
        journal_name = journal_info["title"]
        publisher = journal_info["publisher"]
    except Exception:
        journal_name = "Revista não identificada"
        publisher = ""

    # Buscar exemplos formatados
    examples_text = ""
    try:
        samples = fetch_sample_references(issn, n=3)
        formatted_examples = []
        for s in samples:
            authors = s.get("author", [])
            author_str = "; ".join(
                [f"{a.get('family', '')}, {a.get('given', '')}" for a in authors[:6]]
            )
            if len(authors) > 6:
                author_str += " et al."
            title = s.get("title", [""])[0] if s.get("title") else ""
            vol = s.get("volume", "")
            issue = s.get("issue", "")
            pages = s.get("page", "")
            doi = s.get("DOI", "")
            pub_date = s.get("published-print") or s.get("published-online", {})
            year = ""
            if pub_date and pub_date.get("date-parts"):
                year = str(pub_date["date-parts"][0][0])
            container = s.get("container-title", [""])[0] if s.get("container-title") else journal_name

            formatted_examples.append(
                f"{author_str} ({year}). {title}. {container}, {vol}"
                + (f"({issue})" if issue else "")
                + (f", {pages}" if pages else "")
                + (f". DOI: {doi}" if doi else "")
            )

        if formatted_examples:
            examples_text = (
                "\n\nExemplos de referências recentes desta revista (use como guia de formato):\n"
                + "\n".join(f"  {i+1}. {ex}" for i, ex in enumerate(formatted_examples))
            )
    except Exception:
        examples_text = "\n(Não foi possível obter exemplos de formatação do CrossRef)"

    prompt = f"""Você é um especialista em formatação de referências bibliográficas científicas.

REVISTA: {journal_name}
EDITORA: {publisher}
ISSN: {issn}
{examples_text}

TAREFA: Formate as referências abaixo de acordo com o estilo desta revista.
- Mantenha a ordem das referências.
- Corrija inconsistências de formatação.
- Use o padrão identificado nos exemplos acima.
- Se não houver exemplos suficientes, use o estilo mais provável para a editora {publisher}.
- Numere as referências sequencialmente.

REFERÊNCIAS BRUTAS:
{raw_references}

REFERÊNCIAS FORMATADAS:"""

    return prompt


# ─── Estilos conhecidos de grandes editoras (fallback) ──────────────────────
PUBLISHER_STYLES = {
    "Elsevier": "Vancouver/numbered (sobrenome abreviado, título do artigo, revista abreviada, ano;vol(issue):páginas)",
    "Springer": "Vancouver (sobrenome inicial, título, revista abreviada, ano;vol:páginas, DOI)",
    "Wiley": "Varia por revista — geralmente APA-like ou Vancouver",
    "ACS": "ACS Style (sobrenome, iniciais; título. J. Abbrev. ano, vol, páginas)",
    "Taylor & Francis": "Geralmente APA ou Vancouver, depende da revista",
    "MDPI": "Vancouver/numbered (sobrenome, iniciais; título. Revista ano, vol, páginas)",
    "Nature": "Nature style (numbered, sobrenome, iniciais. título. Revista vol, páginas (ano))",
    "Oxford University Press": "Varia — geralmente Vancouver ou Chicago",
}
