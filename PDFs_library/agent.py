"""
PDFs_library/agent.py — Adaptador LILO para o subagente de biblioteca de PDFs.

Envolve a infraestrutura existente (ingestion, indexing, rag) com a interface
BaseAgent, expondo run() e get_tools() para o orquestrador lilo.py.
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

# Caminho padrão para PDFs (configurável via .env)
import os
PDF_DIR = Path(os.environ.get("PDF_DIR", str(Path(__file__).parent / "data")))


class PDFAgent(BaseAgent):
    """
    Subagente de Biblioteca de PDFs Científicos.

    Capacidades:
    - Sumarização de artigos em diferentes modos (simples, introdução, métodos)
    - Extração de DOI e metadados
    - Busca semântica na biblioteca local de PDFs
    - Análise de figuras/gráficos (quando multimodal disponível)
    """

    name = "pdf"
    description = (
        "Leitura, sumarização e busca semântica em PDFs científicos. "
        "Extração de introdução, métodos, DOI e metadados de artigos."
    )

    KEYWORDS = [
        "pdf", "artigo", "paper", "documento", "arquivo", "resumo",
        "sumarize", "sumarizar", "resumir", "introdução", "métodos",
        "doi", "pubmed", "abstract", "leia", "analise o artigo",
    ]

    # Modos de sumarização herdados do scholaragent/app.py
    MODES = {
        "simple":       "resumo geral objetivo-métodos-resultados-conclusão",
        "introduction": "texto analítico para suportar redação de Introdução científica",
        "methods":      "extração estruturada de Métodos e protocolos",
    }

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
        Processa query sobre PDFs.

        context keys:
            file_path — caminho para PDF específico
            mode      — "simple" | "introduction" | "methods"
            doi       — DOI para buscar metadados
        """
        query     = sanitize_query(query)
        file_path = context.get("file_path", "")
        mode      = context.get("mode", "simple")
        doi       = context.get("doi", "")

        self.log.info(f"PDF query: {truncate(query, 80)} | mode={mode}")

        # Se há arquivo → sumarizar
        if file_path:
            return self._summarize_file(file_path, mode, query)

        # Se há DOI → buscar metadados
        if doi:
            return self._lookup_doi(doi)

        # Busca semântica na biblioteca
        return self._semantic_search(query)

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "pdf_summarize",
                "description": "Sumariza um artigo científico em PDF em diferentes modos (simples, introdução, métodos).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Caminho absoluto para o PDF"},
                        "mode": {
                            "type": "string",
                            "enum": ["simple", "introduction", "methods"],
                            "description": "Modo de sumarização",
                        },
                        "query": {"type": "string", "description": "Pergunta específica sobre o artigo (opcional)"},
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "pdf_search",
                "description": "Busca semântica na biblioteca local de PDFs científicos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termos ou pergunta para buscar nos PDFs"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "pdf_list",
                "description": "Lista PDFs disponíveis na biblioteca local.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {"type": "string", "description": "Filtro por nome ou assunto (opcional)"},
                    },
                    "required": [],
                },
            },
        ]

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _summarize_file(self, file_path: str, mode: str, extra_query: str = "") -> str:
        """Extrai texto do PDF e envia ao LLM para sumarização."""
        path = Path(file_path)
        if not path.exists():
            return f"[PDFAgent] Arquivo não encontrado: {file_path}"

        text = self._extract_text(path)
        if not text:
            return f"[PDFAgent] Não foi possível extrair texto de: {path.name}"

        # Trunca para caber no contexto do modelo
        text_snippet = truncate(text, 6000)

        system_prompts = {
            "simple": (
                "Você é um pesquisador sênior em bioquímica, biologia molecular e parasitologia. "
                "Resuma o artigo destacando: objetivo, metodologia, resultados-chave e conclusão. "
                "Linguagem técnica. Responda em português brasileiro."
            ),
            "introduction": (
                "Você é um pesquisador sênior escrevendo a Introdução de um artigo científico. "
                "Com base no texto, produza um resumo analítico com: contexto/lacuna, hipótese, "
                "relevância e principais conceitos. Texto corrido, nível doutorado, português."
            ),
            "methods": (
                "Analise a seção de Métodos: desenho experimental, modelos biológicos, "
                "técnicas analíticas, softwares, parâmetros computacionais e estatística. "
                "Formato estruturado. Português brasileiro."
            ),
        }

        system = system_prompts.get(mode, system_prompts["simple"])
        prompt = f"ARTIGO:\n\n{text_snippet}"
        if extra_query:
            prompt += f"\n\nPERGUNTA ESPECÍFICA: {extra_query}"

        try:
            return self.llm.chat(prompt, system=system)
        except Exception as e:
            self.log.error(f"Erro LLM: {e}")
            return f"[PDFAgent] Erro ao processar: {e}"

    def _lookup_doi(self, doi: str) -> str:
        """Busca metadados via CrossRef (sem autenticação)."""
        try:
            import requests
            url = f"https://api.crossref.org/works/{doi}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("message", {})
                title  = data.get("title", ["N/A"])[0]
                authors = ", ".join(
                    f"{a.get('given','')} {a.get('family','')}"
                    for a in data.get("author", [])[:3]
                )
                year   = data.get("published", {}).get("date-parts", [[None]])[0][0]
                journal = data.get("container-title", ["N/A"])[0]
                return f"**{title}**\nAutores: {authors}\nAno: {year}\nRevista: {journal}\nDOI: {doi}"
            return f"[PDFAgent] DOI não encontrado: {doi}"
        except Exception as e:
            return f"[PDFAgent] Erro ao buscar DOI: {e}"

    def _semantic_search(self, query: str) -> str:
        """Lista PDFs disponíveis e responde com contexto da biblioteca."""
        pdfs = self._list_pdfs()
        if not pdfs:
            return (
                f"[PDFAgent] Biblioteca vazia em {PDF_DIR}.\n"
                "Adicione PDFs científicos à pasta PDFs_library/data/ para busca semântica."
            )

        pdf_list = "\n".join(f"- {p.name}" for p in pdfs[:20])
        prompt = (
            f"O usuário perguntou: '{query}'\n\n"
            f"PDFs disponíveis na biblioteca:\n{pdf_list}\n\n"
            "Identifique quais PDFs são mais relevantes para a pergunta e explique por quê. "
            "Se precisar de mais contexto, indique qual PDF deve ser aberto."
        )
        try:
            return self.llm.chat(prompt)
        except Exception as e:
            return f"[PDFAgent] Erro: {e}\n\nPDFs disponíveis:\n{pdf_list}"

    def _extract_text(self, path: Path) -> str:
        """Extrai texto de PDF usando PyMuPDF (fitz) ou pdfminer."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            pass
        try:
            from pdfminer.high_level import extract_text
            return extract_text(str(path))
        except Exception:
            pass
        return ""

    def _list_pdfs(self) -> list[Path]:
        """Lista todos os PDFs na biblioteca."""
        if not PDF_DIR.exists():
            return []
        return sorted(PDF_DIR.rglob("*.pdf"))[:50]
