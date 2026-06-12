"""
agents/paper/agent.py — Subagente de REDAÇÃO CIENTÍFICA do LILO (V13).
====================================================================
Porta a skill `build_paper` (originalmente para o Claude) para o LILO. O
"escritor" é um modelo forte via Ollama (default gpt-oss:120b-cloud, que NÃO
usa a GPU local) — config por LILO_PAPER_MODEL.

Princípios (de lilo_skills/skills/build_paper/reference/principios_cientificos.md):
distinguir fato/interpretação/especulação; nunca inventar números OU referências;
nunca causalidade a partir de correlação; limitações explícitas; profundidade e
rigor de revisão por pares. Referências vêm SEMPRE de fontes reais
(shared.research_sources / ScholarAgent) — o modelo não pode fabricá-las.

Fluxo: outline -> seções (redigidas com refs reais) -> fonte Markdown única ->
build (DOCX/TEX/PDF via assets/build.sh da skill portada).

Tools: paper_outline, paper_section, paper_references, paper_build, paper_draft.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.utils import load_env, sanitize_query, truncate
from shared.logger import get_logger

load_env()
log = get_logger("PaperAgent")

# Skill portada (scripts de build, template, reference, perfis).
_SKILL = _ROOT / "lilo_skills" / "skills" / "build_paper"

# Escritor: modelo forte. Default cloud (sem GPU local). Override por env.
PAPER_MODEL = os.getenv("LILO_PAPER_MODEL", "gpt-oss:120b-cloud")

# Seções canônicas IMRaD (rótulos PT; o template define a notação).
_SECTIONS = ("abstract", "introducao", "metodos", "resultados",
             "discussao", "conclusao")

_WRITER_SYSTEM = (
    "Voce e um redator cientifico senior (PhD), escrevendo para publicacao com "
    "revisao por pares em bioquimica/biologia molecular/omics/farmacologia. "
    "REGRAS INEGOCIAVEIS:\n"
    "1. NUNCA invente numeros, resultados ou referencias. Use SOMENTE os dados e "
    "as referencias fornecidos no contexto; se faltar, declare a lacuna.\n"
    "2. Distinga FATO (dado), INTERPRETACAO e ESPECULACAO explicitamente.\n"
    "3. Nunca infira causalidade a partir de correlacao.\n"
    "4. Declare limitacoes e hipoteses alternativas.\n"
    "5. Terminologia tecnica precisa; profundidade > concisao; itálico para "
    "especies/genes (*Trypanosoma cruzi*); notacao pandoc (Mg^2+^, 10^-5^).\n"
    "Responda em portugues brasileiro, salvo pedido explicito de ingles."
)


class PaperAgent(BaseAgent):
    """Redação científica: outline, seções com refs reais, build de DOCX/TEX/PDF."""

    name = "paper"
    description = (
        "Redacao cientifica (skill build_paper): estrutura, redige secoes com "
        "referencias REAIS (PubMed/OpenAlex/Europe PMC), monta fonte Markdown e "
        "builda DOCX/TEX/PDF (pandoc+tectonic). Escritor forte via Ollama Cloud."
    )

    KEYWORDS = [
        "paper", "manuscrito", "artigo cientifico", "redacao cientifica",
        "build_paper", "introducao", "metodos", "resultados", "discussao",
        "abstract", "resumo", "submissao", "periodico", "revista",
        "responder revisores", "escrever o paper", "montar o artigo",
    ]
    cost_tier = "ollama"
    local_only = False   # usa modelo cloud por padrao (gpt-oss:120b-cloud)
    latency_class = "slow"

    def __init__(self):
        super().__init__()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    # ── escrita (modelo forte) ───────────────────────────────────────────────
    def _write(self, prompt: str, max_tokens: int = 4096) -> str:
        try:
            return self.llm.chat(prompt, system=_WRITER_SYSTEM,
                                  model=PAPER_MODEL, temperature=0.3,
                                  max_tokens=max_tokens)
        except Exception as e:
            log.error("Escritor (%s) falhou: %s", PAPER_MODEL, e)
            return "[PaperAgent ERRO no escritor (%s): %s]" % (PAPER_MODEL, e)

    # ── referências REAIS (anti-invenção) ────────────────────────────────────
    def _references(self, topic: str, k: int = 8) -> list[dict]:
        try:
            from shared import research_sources as rs
            agg = rs.search_all(topic, ["openalex", "pubmed", "europepmc",
                                        "crossref"], max_results=max(2, k // 4))
            return agg.get("results", [])[:k]
        except Exception as e:
            log.warning("Busca de referencias falhou: %s", e)
            return []

    @staticmethod
    def _fmt_refs(refs: list[dict]) -> str:
        if not refs:
            return "(nenhuma referencia recuperada — NAO invente; sinalize a lacuna)"
        out = []
        for i, r in enumerate(refs, 1):
            out.append("[%d] %s. %s (%s). %s" % (
                i, r.get("authors", "") or "s/ autores",
                r.get("title", ""), r.get("year", "s/d"),
                r.get("url", "") or r.get("id", "")))
        return "\n".join(out)

    # ── perfil da revista (normas empiricas via fontes reais) ────────────────
    def _journal_hint(self, journal: str) -> str:
        if not journal:
            return ""
        try:
            from shared import research_sources as rs
            sample = rs.search_all(journal, ["openalex", "crossref"],
                                   max_results=3).get("results", [])
            if sample:
                titles = "; ".join(s.get("title", "")[:80] for s in sample[:3])
                return ("Periodico-alvo: %s. Amostra de artigos recentes (calibre "
                        "esperado): %s" % (journal, titles))
        except Exception as e:
            log.debug("journal_hint falhou: %s", e)
        return "Periodico-alvo: %s" % journal

    # ── BaseAgent ─────────────────────────────────────────────────────────────
    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        query = sanitize_query(query)
        ctx = context or {}
        mode = ctx.get("mode", "draft")
        journal = ctx.get("journal", "")
        log.info("Paper: mode=%s journal=%s | %s", mode, journal,
                 truncate(query, 70))

        if mode == "references":
            refs = self._references(query, int(ctx.get("k", 8)))
            return "## Referencias reais\n\n" + self._fmt_refs(refs)

        if mode == "build":
            return self._build(ctx.get("root", str(_ROOT / "PAPER_out")))

        if mode == "outline":
            jh = self._journal_hint(journal)
            return self._write(
                "Crie a ESTRUTURA (outline) de um manuscrito cientifico para a "
                "tarefa abaixo: seções IMRaD com 1-2 frases de escopo cada e "
                "metas de profundidade. %s\n\nTAREFA: %s" % (jh, query))

        if mode == "section":
            section = ctx.get("section", "introducao")
            refs = self._references(query, int(ctx.get("k", 8)))
            jh = self._journal_hint(journal)
            return self._write(
                "Redija a secao '%s' de um manuscrito cientifico. %s\n\n"
                "TAREFA/CONTEUDO: %s\n\nREFERENCIAS REAIS disponiveis (use SO "
                "estas; cite como [n]):\n%s" % (section, jh, query,
                                                self._fmt_refs(refs)),
                max_tokens=6144)

        # mode == "draft": outline + seções principais encadeadas + refs.
        return self._draft(query, journal, ctx)

    def _draft(self, query: str, journal: str, ctx: dict) -> str:
        jh = self._journal_hint(journal)
        refs = self._references(query, int(ctx.get("k", 10)))
        refs_block = self._fmt_refs(refs)
        parts = ["# Manuscrito (rascunho LILO)\n", jh, ""]
        outline = self._write(
            "Outline IMRaD conciso para: %s\n%s" % (query, jh), max_tokens=1024)
        parts += ["## Outline\n", outline, ""]
        for sec in ("abstract", "introducao", "metodos", "resultados",
                    "discussao"):
            log.info("  redigindo secao: %s", sec)
            txt = self._write(
                "Redija a secao '%s' do manuscrito. %s\n\nTEMA/DADOS: %s\n\n"
                "OUTLINE:\n%s\n\nREFERENCIAS REAIS (use SO estas, cite [n]):\n%s"
                % (sec, jh, query, outline[:1200], refs_block), max_tokens=4096)
            parts += ["## %s\n" % sec.capitalize(), txt, ""]
        parts += ["## Referencias\n", refs_block]
        return "\n".join(parts)

    def _build(self, root: str) -> str:
        build_sh = _SKILL / "assets" / "build.sh"
        if not build_sh.exists():
            return "[PaperAgent] build.sh nao encontrado em %s" % build_sh
        try:
            r = subprocess.run(["bash", str(build_sh), root],
                               capture_output=True, text=True, timeout=600)
            return "## Build\n\n```\n%s\n%s\n```" % (
                r.stdout[-2000:], r.stderr[-800:])
        except Exception as e:
            return "[PaperAgent] build falhou: %s" % e

    def get_tools(self) -> list[dict]:
        _q = {"query": {"type": "string", "description": "Tema/dados do manuscrito"}}
        return [
            {"name": "paper_outline",
             "description": "Gera a estrutura (outline IMRaD) de um manuscrito.",
             "inputSchema": {"type": "object", "properties": {
                 **_q, "journal": {"type": "string"}}, "required": ["query"]}},
            {"name": "paper_section",
             "description": "Redige UMA secao com referencias reais (cite [n]).",
             "inputSchema": {"type": "object", "properties": {
                 **_q, "section": {"type": "string",
                                   "enum": list(_SECTIONS)},
                 "journal": {"type": "string"}}, "required": ["query", "section"]}},
            {"name": "paper_references",
             "description": "Busca referencias REAIS (PubMed/OpenAlex/EuropePMC).",
             "inputSchema": {"type": "object", "properties": {
                 **_q, "k": {"type": "integer", "default": 8}},
                 "required": ["query"]}},
            {"name": "paper_draft",
             "description": "Rascunho completo: outline + secoes + refs reais.",
             "inputSchema": {"type": "object", "properties": {
                 **_q, "journal": {"type": "string"}}, "required": ["query"]}},
            {"name": "paper_build",
             "description": "Builda DOCX/TEX/PDF da fonte Markdown (pandoc+tectonic).",
             "inputSchema": {"type": "object", "properties": {
                 "root": {"type": "string", "description": "Raiz do projeto PAPER"}},
                 "required": ["root"]}},
        ]

    def capabilities(self) -> dict:
        return {"name": self.name, "keywords": self.KEYWORDS,
                "writer_model": PAPER_MODEL, "skill_path": str(_SKILL),
                "sections": list(_SECTIONS)}

    def health(self) -> dict:
        return {"status": "ok", "writer_model": PAPER_MODEL,
                "skill_present": _SKILL.exists(),
                "build_sh": (_SKILL / "assets" / "build.sh").exists()}
