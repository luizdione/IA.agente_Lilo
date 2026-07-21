"""
scholaragent/agent.py — Adaptador LILO para o subagente de busca acadêmica.

Envolve as fontes (PubMed, arXiv, Scholar) com interface BaseAgent.
Reaproveita ollama_client.py e reference_formatter.py existentes.
"""

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.models import WORKER_CLOUD
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
        # V10.4: fontes externas adicionais (paridade com o Claude).
        "ensaio clínico", "ensaios clínicos", "clinical trial", "clinicaltrials",
        "alvo terapêutico", "open targets", "gene-doença", "target",
        "crossref", "doi", "semantic scholar", "npi", "provedor de saúde",
        # V12.2: novas fontes
        "openalex", "google scholar", "google acadêmico", "google academico",
        "europe pmc", "europepmc", "google books", "livro", "livros",
        "wikipedia", "wikipédia", "enciclopédia",
    ]

    # V9 (2026-05-22): roteamento cost-aware no Villa_Lobos.
    # Sumarização local, mas faz chamadas externas (PubMed/arXiv/CrossRef)
    # -> sem custo de nuvem LLM, porém latência alta por I/O de rede.
    cost_tier = "ollama"
    local_only = True
    latency_class = "slow"

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
            source    — "auto" | "all" | "pubmed" | "arxiv" | "clinicaltrials"
                        | "opentargets" | "npi" | "crossref" | "semanticscholar"
            max_results — int (default 5)
            synthesize  — bool (default True) → usa LLM para sintetizar resultados

        V10.4 (2026-05-31): paridade de pesquisa externa com o Claude. Além de
        PubMed/arXiv (nativos), delega a shared.research_sources para
        ClinicalTrials.gov, Open Targets, NPI Registry, Crossref e Semantic
        Scholar — todas APIs públicas (sem chave). source="all" agrega todas.
        """
        query      = sanitize_query(query)
        source     = context.get("source", "auto")
        max_res    = int(context.get("max_results", 5))
        synthesize = context.get("synthesize", True)

        # V13.1: modo REVISAO de literatura (busca ampla + dedup + revisao
        # estruturada). Acionado por context mode/source == "review".
        if context.get("mode") == "review" or source == "review":
            return self._review(query, int(context.get("max_results", 20)))

        self.log.info(f"Scholar query: {truncate(query, 80)} | source={source}")

        # Fontes delegadas ao módulo research_sources (públicas).
        # V12.2 (2026-06-11): +openalex (substituto do Google Scholar),
        # +europepmc, +googlebooks, +wikipedia.
        _EXTERNAL = {"clinicaltrials", "opentargets", "npi",
                     "crossref", "semanticscholar", "openalex", "europepmc",
                     "googlebooks", "wikipedia"}
        # source="all" => cobertura acadêmica máxima (sem arxiv, que é nativo).
        _ALL = ["pubmed", "europepmc", "openalex", "crossref",
                "semanticscholar", "googlebooks", "clinicaltrials",
                "opentargets", "npi"]

        results = []
        if source == "all":
            try:
                from shared import research_sources as _rs
                agg = _rs.search_all(query, _ALL, max_results=max_res)
                results += agg.get("results", [])
            except Exception as e:
                self.log.warning(f"research_sources(all) falhou: {e}")
            results += self._search_arxiv(query, max_res)
        elif source in _EXTERNAL:
            try:
                from shared import research_sources as _rs
                results += _rs._DISPATCH[source](query, max_res)
            except Exception as e:
                self.log.warning(f"fonte {source} falhou: {e}")
        else:
            if source in ("auto", "pubmed"):
                results += self._search_pubmed(query, max_res)
            if source in ("auto", "arxiv") and len(results) < max_res:
                results += self._search_arxiv(query, max_res - len(results))

        # Normaliza dicts do research_sources (id) p/ o formatador (pmid/source).
        for r in results:
            r.setdefault("pmid", r.get("id", ""))
            r.setdefault("source", "")
            r.setdefault("authors", "")
            r.setdefault("year", "")

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
                            "enum": ["auto", "all", "pubmed", "arxiv",
                                     "openalex", "europepmc", "googlebooks",
                                     "wikipedia", "clinicaltrials",
                                     "opentargets", "npi", "crossref",
                                     "semanticscholar"],
                            "description": ("Fonte de busca (padrão: auto = "
                                            "pubmed+arxiv). 'all' agrega as "
                                            "acadêmicas; openalex substitui o "
                                            "Google Scholar; googlebooks=livros; "
                                            "wikipedia=conhecimento geral."),
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
            {
                "name": "scholar_review",
                "description": ("Revisao de literatura ESTRUTURADA: busca ampla "
                                "multi-fonte + deduplicacao + estado da arte/"
                                "consensos/lacunas/direcoes, com referencias reais. "
                                "Ideal para Introducao/Discussao de um paper."),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Tema da revisao"},
                        "max_results": {"type": "integer", "description": "Max artigos (padrão: 20)"},
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

    # ── Revisão de literatura (V13.1) ─────────────────────────────────────────
    @staticmethod
    def _dedup(results: list[dict]) -> list[dict]:
        """Deduplica artigos entre fontes por DOI normalizado, senão por
        prefixo do título (minusculo, alfanumerico)."""
        import re as _re
        seen, out = set(), []
        for r in results:
            doi = (r.get("id", "") or "").lower()
            doi = doi.split("doi.org/")[-1].strip("/ ") if "10." in doi else ""
            title = _re.sub(r"[^a-z0-9]", "", (r.get("title", "") or "").lower())[:50]
            key = doi or title
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    def _review(self, query: str, max_results: int = 20) -> str:
        """Revisão de literatura: busca ampla nas fontes academicas, deduplica
        e sintetiza uma REVISAO estruturada (estado da arte, consensos,
        controversias, lacunas) com referencias REAIS numeradas. Escritor
        configuravel (LILO_REVIEW_MODEL; default = cloud, sem GPU local)."""
        import os as _os
        results = []
        try:
            from shared import research_sources as rs
            per = max(2, max_results // 5)
            agg = rs.search_all(query, ["pubmed", "europepmc", "openalex",
                                        "crossref", "semanticscholar"],
                                max_results=per)
            results += agg.get("results", [])
        except Exception as e:
            self.log.warning(f"review: research_sources falhou: {e}")
        results += self._search_arxiv(query, 5)
        for r in results:
            r.setdefault("authors", "")
            r.setdefault("year", "")
            r.setdefault("source", "")
        results = self._dedup(results)[:max_results]
        if not results:
            return f"[ScholarAgent] Nenhum artigo para revisar: '{query}'"
        formatted = self._format_results(results)
        model = _os.getenv("LILO_REVIEW_MODEL", WORKER_CLOUD)
        system = (
            "Voce e um pesquisador senior redigindo uma REVISAO DE LITERATURA "
            "para a secao de Introducao/Discussao de um artigo. Use SOMENTE os "
            "artigos fornecidos; cite como [n]. NUNCA invente dados ou refs. "
            "Distinga consenso de controversia; aponte lacunas. PT-BR tecnico."
        )
        prompt = (
            f"TEMA DA REVISAO: {query}\n\nARTIGOS (use so estes, cite [n]):\n"
            f"{formatted}\n\nEscreva a revisao estruturada em 4 blocos: "
            "**Estado da arte**, **Consensos**, **Controversias/lacunas**, "
            "**Direcoes futuras**. Densa e tecnica."
        )
        try:
            review = self.llm.chat(prompt, system=system, model=model,
                                   temperature=0.3, max_tokens=6144)
        except Exception as e:
            self.log.error(f"review LLM ({model}) falhou: {e}")
            return formatted
        return (f"# Revisao de literatura: {query}\n\n{review}\n\n---\n\n"
                f"## Referencias ({len(results)})\n\n{formatted}")
