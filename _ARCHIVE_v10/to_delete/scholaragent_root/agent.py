"""
scholaragent/agent.py — Adaptador LILO para o subagente de busca acadêmica.

Envolve as fontes (PubMed, arXiv, Scholar) com interface BaseAgent.
Reaproveita ollama_client.py e reference_formatter.py existentes.
"""

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.utils import load_env, sanitize_query, truncate

load_env()


class ScholarAgent(BaseAgent):
    """
    Subagente de Busca Acadêmica.

    Fontes:
    - PubMed (via E-utilities API, sem autenticação)
    - arXiv (via API pública)
    - CrossRef (metadados DOI)
    - Resumo/síntese via LLM local

    Especialidade: biologia molecular, bioinformática, genômica,
                   parasitologia, docking molecular.
    """

    name = "scholar"
    description = (
        "Busca e síntese de literatura científica via PubMed, arXiv e CrossRef. "
        "Retorna artigos relevantes com resumos, DOIs e formatação de referências."
    )

    KEYWORDS = [
        "paper", "pubmed", "arxiv", "scholar", "pesquisa", "literatura",
        "referência", "artigos sobre", "estudos de", "publicações",
        "buscar artigos", "encontrar papers", "review", "meta-análise",
    ]

    def __init__(self):
        super().__init__()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    # ── Interface BaseAgent ──────────────────────────────────────────────────

    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        """
        Processa busca acadêmica.

        context keys:
            source    — "pubmed" | "arxiv" | "crossref" | "auto"
            max_results — int (default 5)
            synthesize  — bool (default True) → usa LLM para sintetizar resultados
        """
        query      = sanitize_query(query)
        source     = context.get("source", "auto")
        max_res    = int(context.get("max_results", 5))
        synthesize = context.get("synthesize", True)

        self.log.info(f"Scholar query: {truncate(query, 80)} | source={source}")

        # Busca nas fontes
        results = []

        if source in ("auto", "pubmed"):
            results += self._search_pubmed(query, max_res)

        if source in ("auto", "arxiv") and len(results) < max_res:
            results += self._search_arxiv(query, max_res - len(results))

        if not results:
            return f"[ScholarAgent] Nenhum resultado encontrado para: '{query}'"

        # Formata resultado
        formatted = self._format_results(results)

        if not synthesize:
            return formatted

        # Síntese via LLM
        return self._synthesize(query, formatted)

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "scholar_search",
                "description": "Busca artigos científicos no PubMed e arXiv sobre um tema.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termos de busca ou pergunta científica"},
                        "source": {
                            "type": "string",
                            "enum": ["auto", "pubmed", "arxiv"],
                            "description": "Fonte de busca (padrão: auto)",
                        },
                        "max_results": {"type": "integer", "description": "Máximo de resultados (padrão: 5)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "scholar_synthesize",
                "description": "Busca e sintetiza literatura científica com análise crítica via LLM.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Tema ou hipótese a investigar"},
                        "max_results": {"type": "integer", "description": "Número de artigos (padrão: 5)"},
                    },
                    "required": ["query"],
                },
            },
        ]

    # ── Buscadores ───────────────────────────────────────────────────────────

    def _search_pubmed(self, query: str, max_results: int = 5) -> list[dict]:
        """Busca no PubMed via E-utilities (sem API key)."""
        import requests
        BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        try:
            # Busca IDs
            r = requests.get(
                f"{BASE}/esearch.fcgi",
                params={"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"},
                timeout=15,
            )
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            # Busca resumos
            r2 = requests.get(
                f"{BASE}/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
                timeout=15,
            )
            data = r2.json().get("result", {})

            results = []
            for uid in ids:
                item = data.get(uid, {})
                if not item:
                    continue
                results.append({
                    "title":   item.get("title", "N/A"),
                    "authors": ", ".join(a.get("name","") for a in item.get("authors",[])[:3]),
                    "year":    item.get("pubdate","")[:4],
                    "source":  item.get("source",""),
                    "pmid":    uid,
                    "url":     f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                })
            return results
        except Exception as e:
            self.log.warning(f"PubMed erro: {e}")
            return []

    def _search_arxiv(self, query: str, max_results: int = 5) -> list[dict]:
        """Busca no arXiv via API pública."""
        import requests
        import xml.etree.ElementTree as ET
        try:
            r = requests.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": f"all:{query}", "max_results": max_results},
                timeout=15,
            )
            root = ET.fromstring(r.text)
            NS = "http://www.w3.org/2005/Atom"

            results = []
            for entry in root.findall(f"{{{NS}}}entry"):
                arxiv_id = entry.find(f"{{{NS}}}id").text.split("/abs/")[-1]
                results.append({
                    "title":   entry.find(f"{{{NS}}}title").text.strip(),
                    "authors": ", ".join(
                        a.find(f"{{{NS}}}name").text
                        for a in entry.findall(f"{{{NS}}}author")[:3]
                    ),
                    "year":    entry.find(f"{{{NS}}}published").text[:4],
                    "source":  "arXiv",
                    "pmid":    arxiv_id,
                    "url":     f"https://arxiv.org/abs/{arxiv_id}",
                })
            return results
        except Exception as e:
            self.log.warning(f"arXiv erro: {e}")
            return []

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _format_results(self, results: list[dict]) -> str:
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. **{r['title']}**\n"
                f"   Autores: {r['authors']} ({r['year']}) — {r['source']}\n"
                f"   🔗 {r['url']}"
            )
        return "\n\n".join(lines)

    def _synthesize(self, query: str, formatted: str) -> str:
        system = (
            "Você é um pesquisador sênior em bioinformática e biologia molecular. "
            "Analise os artigos encontrados e forneça uma síntese crítica: "
            "tendências, consensos, lacunas e relevância para a pergunta. "
            "Português brasileiro, linguagem técnica."
        )
        prompt = (
            f"PERGUNTA DE PESQUISA: {query}\n\n"
            f"ARTIGOS ENCONTRADOS:\n{formatted}\n\n"
            "Forneça uma síntese crítica de 3-5 parágrafos sobre o estado da arte neste tema."
        )
        try:
            synthesis = self.llm.chat(prompt, system=system)
            return f"## Síntese\n\n{synthesis}\n\n---\n\n## Artigos\n\n{formatted}"
        except Exception as e:
            self.log.error(f"Erro síntese LLM: {e}")
            return formatted
