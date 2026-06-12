"""
Prism AI Copilot — Main Agent (Orquestrador Interno)
=====================================================
Herda BaseAgent e orquestra o pipeline de 6 sub-agentes:
  ingest → classify → stats → plot → write → export

Integra-se ao orquestrador LILO como 5º subagente.
"""

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import asdict, is_dataclass

import sys
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.logger import get_logger

log = get_logger("PrismAgent")


def _safe_dict(obj):
    """Converte dataclass para dict, removendo campos não-serializáveis."""
    if is_dataclass(obj) and not isinstance(obj, type):
        d = {}
        for k, v in asdict(obj).items():
            if k == "df":
                continue  # pular DataFrames
            d[k] = v
        return d
    return obj


class PrismAgent(BaseAgent):
    """
    Agente de Análise Científica Automatizada.

    Pipeline: ingest → classify → stats → visualize → write → export
    """

    name = "prism"
    description = (
        "Análise científica automatizada: detecta tipo de experimento, "
        "seleciona teste estatístico, gera gráficos padrão publicação, "
        "escreve seção Resultados e exporta .pzfx (GraphPad Prism). "
        "Aceita .xlsx e .csv."
    )

    # V9 (2026-05-22): roteamento cost-aware no Villa_Lobos.
    # Pipeline estatístico + gráficos + export local; custo baixo, latência média.
    # (keywords vêm de config/villa/domains.yaml via fallback do BaseAgent.)
    cost_tier = "ollama"
    local_only = True
    latency_class = "medium"

    def __init__(self):
        super().__init__()
        # Lazy-load sub-agentes
        self._ingestion = None
        self._classification = None
        self._stats = None
        self._visualization = None
        self._writing = None
        self._export = None

    # ── Lazy loading ─────────────────────────────────────────────────────

    @property
    def ingestion(self):
        if not self._ingestion:
            from .ingestion_agent import IngestionAgent
            self._ingestion = IngestionAgent()
        return self._ingestion

    @property
    def classification(self):
        if not self._classification:
            from .classification_agent import ClassificationAgent
            self._classification = ClassificationAgent()
        return self._classification

    @property
    def stats(self):
        if not self._stats:
            from .stats_agent import StatsAgent
            self._stats = StatsAgent()
        return self._stats

    @property
    def visualization(self):
        if not self._visualization:
            from .visualization_agent import VisualizationAgent
            self._visualization = VisualizationAgent()
        return self._visualization

    @property
    def writing(self):
        if not self._writing:
            from .writing_agent import WritingAgent
            self._writing = WritingAgent()
        return self._writing

    @property
    def export(self):
        if not self._export:
            from .export_agent import ExportAgent
            self._export = ExportAgent()
        return self._export

    # ── Interface BaseAgent ──────────────────────────────────────────────

    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        """
        Ponto de entrada do pipeline Prism AI.

        Args:
            query: pode ser:
                - caminho de arquivo (executa pipeline completo)
                - "analyze <path>"
                - "stats <path>"
                - "plot <path>"
                - "export <path>"
            context: dict com file_path, output_dir, language, alpha, etc.

        Returns:
            Texto com resumo dos resultados (Markdown).
        """
        file_path = context.get("file_path") or self._extract_path(query)
        if not file_path:
            return self._help_text()

        output_dir = context.get("output_dir") or str(
            Path(file_path).parent / "prism_output"
        )

        # Configuração
        config = {
            "language": context.get("language", "en"),
            "alpha": context.get("alpha", 0.05),
            "dpi": context.get("dpi", 300),
            "enhance_with_llm": context.get("enhance_with_llm", True),
            "export_csv": context.get("export_csv", True),
        }

        # V13.3: modo EDA (perfil exploratório rápido), antes do pipeline pesado.
        _q = (query or "").strip().lower()
        if context.get("mode") == "eda" or _q.startswith(("eda", "perfil", "profile")):
            try:
                return self._eda(file_path, output_dir, config)
            except Exception as e:
                log.error(f"EDA falhou: {e}", exc_info=True)
                return f"## ❌ Erro no EDA\n\n{e}"

        # Detectar modo parcial
        mode = self._detect_mode(query)

        try:
            return self._run_pipeline(file_path, output_dir, config, mode)
        except Exception as e:
            log.error(f"Pipeline falhou: {e}", exc_info=True)
            return f"## ❌ Erro no Prism AI\n\n{e}\n\nVerifique o arquivo e tente novamente."

    def get_tools(self) -> list[dict]:
        """Retorna ferramentas MCP do Prism AI."""
        return [
            {
                "name": "prism_analyze",
                "description": (
                    "Executa análise científica completa em dados experimentais. "
                    "Detecta tipo de experimento, seleciona teste estatístico, "
                    "gera gráficos e texto de resultados. Aceita .xlsx e .csv."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Caminho para arquivo de dados (.xlsx ou .csv)",
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Diretório para salvar resultados (opcional)",
                        },
                        "language": {
                            "type": "string",
                            "enum": ["en", "pt"],
                            "description": "Idioma do texto de resultados",
                            "default": "en",
                        },
                        "alpha": {
                            "type": "number",
                            "description": "Nível de significância (default: 0.05)",
                            "default": 0.05,
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "prism_classify",
                "description": (
                    "Classifica o tipo de experimento a partir de dados. "
                    "Retorna tipo, variável, testes sugeridos."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Caminho para arquivo de dados",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "prism_audit",
                "description": (
                    "Audita uma análise estatística existente: "
                    "detecta erros, sugere correções."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Caminho para arquivo de dados",
                        },
                        "claimed_test": {
                            "type": "string",
                            "description": "Teste estatístico que foi usado (para auditoria)",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "prism_eda",
                "description": (
                    "Perfil exploratório RÁPIDO de um dataset (.csv/.xlsx): "
                    "dimensões, tipos, %nulos, cardinalidade, describe das "
                    "numéricas, histogramas e heatmap de correlação. Visão "
                    "inicial leve (sem teste estatístico — use prism_analyze p/ isso)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string",
                                      "description": "Caminho .csv/.xlsx"},
                        "output_dir": {"type": "string"},
                    },
                    "required": ["file_path"],
                },
            },
        ]

    def health(self) -> dict:
        """Retorna status do Prism AI."""
        deps = {}
        for pkg in ["pandas", "numpy", "scipy", "matplotlib", "seaborn"]:
            try:
                __import__(pkg)
                deps[pkg] = "ok"
            except ImportError:
                deps[pkg] = "missing"

        all_ok = all(v == "ok" for v in deps.values())
        return {
            "status": "ok" if all_ok else "degraded",
            "dependencies": deps,
            "sub_agents": [
                "ingestion", "classification", "stats",
                "visualization", "writing", "export",
            ],
        }

    # ── EDA / perfil exploratório (V13.3) ────────────────────────────────
    def _eda(self, file_path: str, output_dir: str, config: dict) -> str:
        """Perfil exploratório RÁPIDO de um dataset (.csv/.xlsx), determinístico
        (pandas + matplotlib, sem LLM): dimensões, tipos/%nulos/cardinalidade,
        describe das numéricas, histogramas e heatmap de correlação. Complementa
        prism_analyze (pipeline estatístico pesado) com uma visão inicial leve.
        """
        import pandas as pd
        from pathlib import Path as _P
        _P(output_dir).mkdir(parents=True, exist_ok=True)
        fp = str(file_path)
        try:
            df = (pd.read_excel(fp) if fp.lower().endswith((".xlsx", ".xls"))
                  else pd.read_csv(fp))
        except Exception as e:
            return "## ❌ EDA — erro ao ler %s\n\n%s" % (fp, e)
        n, m = df.shape
        num = df.select_dtypes("number")
        lines = ["## 📊 Prism AI — EDA (perfil exploratório)\n",
                 "**Arquivo:** %s" % fp,
                 "**Dimensões:** %d linhas × %d colunas\n" % (n, m),
                 "### Colunas", "| coluna | tipo | %nulos | n_únicos |",
                 "|---|---|---|---|"]
        for c in df.columns:
            lines.append("| %s | %s | %.1f%% | %d |" % (
                c, df[c].dtype, 100 * df[c].isna().mean(), df[c].nunique()))
        if not num.empty:
            lines += ["", "### Estatística descritiva (numéricas)", "```",
                      num.describe().round(3).to_string(), "```"]
        figs = []
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            for c in list(num.columns)[:6]:
                fig, ax = plt.subplots(figsize=(4, 3))
                num[c].dropna().hist(ax=ax, bins=20)
                ax.set_title(str(c))
                pth = _P(output_dir) / ("eda_hist_%s.png" % str(c)[:30])
                fig.savefig(pth, dpi=120, bbox_inches="tight")
                plt.close(fig)
                figs.append(str(pth))
            if num.shape[1] >= 2:
                corr = num.corr()
                fig, ax = plt.subplots(figsize=(5, 4))
                im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
                ax.set_xticks(range(len(corr)))
                ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
                ax.set_yticks(range(len(corr)))
                ax.set_yticklabels(corr.columns, fontsize=7)
                fig.colorbar(im)
                ax.set_title("Correlação (Pearson)")
                pth = _P(output_dir) / "eda_corr.png"
                fig.savefig(pth, dpi=120, bbox_inches="tight")
                plt.close(fig)
                figs.append(str(pth))
        except Exception as e:
            lines.append("\n(gráficos: falha — %s)" % e)
        if figs:
            lines += ["", "### Gráficos (%d)" % len(figs)] + ["- %s" % f for f in figs]
        return "\n".join(lines)

    # ── Pipeline ─────────────────────────────────────────────────────────

    def _run_pipeline(self, file_path: str, output_dir: str,
                      config: dict, mode: str = "full") -> str:
        """Executa o pipeline completo ou parcial."""
        log.info(f"Pipeline Prism AI: {file_path} | mode={mode}")

        # 1. INGEST
        log.info("── Stage 1/6: Ingestion ──")
        ingested = self.ingestion.run(file_path, config)

        if mode == "classify_only":
            cls = self.classification.run(ingested)
            return self._format_classification(cls)

        # 2. CLASSIFY
        log.info("── Stage 2/6: Classification ──")
        cls = self.classification.run(ingested)

        # 3. STATS
        log.info("── Stage 3/6: Statistics ──")
        stats_result = self.stats.run(ingested, cls, config)

        if mode == "stats_only":
            return self._format_stats(stats_result)

        # 4. VISUALIZE
        log.info("── Stage 4/6: Visualization ──")
        figures = self.visualization.run(ingested, cls, stats_result, output_dir, config)

        if mode == "plot_only":
            return self._format_figures(figures)

        # 5. WRITE
        log.info("── Stage 5/6: Scientific Writing ──")
        writing = self.writing.run(ingested, cls, stats_result, figures, config)

        # 6. EXPORT
        log.info("── Stage 6/6: Export ──")
        export = self.export.run(ingested, cls, stats_result, output_dir, config)

        # Resultado consolidado
        return self._format_full_result(ingested, cls, stats_result,
                                         figures, writing, export)

    # ── Formatação ───────────────────────────────────────────────────────

    def _format_full_result(self, data, cls, stats, figures, writing, export) -> str:
        """Formata resultado completo em Markdown."""
        lines = ["## 🔬 Prism AI — Análise Completa\n"]

        # Classificação
        lines.append(f"**Experimento:** {cls.experiment_type.value} "
                     f"(confiança: {cls.confidence:.0%})")
        lines.append(f"**Variável:** {cls.variable_type.value}")
        lines.append(f"**Grupos:** {cls.n_groups} | "
                     f"**Pareado:** {'Sim' if cls.is_paired else 'Não'}")
        lines.append(f"**Justificativa:** {cls.reasoning}\n")

        # Estatística
        lines.append(f"### Teste Estatístico: {stats.test_full_name}")
        p_str = f"p = {stats.p_value:.4f}" if stats.p_value >= 0.001 else "p < 0.001"
        lines.append(f"- Estatística: {stats.statistic:.4f}")
        lines.append(f"- {p_str}")
        if stats.effect_size is not None:
            lines.append(f"- {stats.effect_size_name}: {stats.effect_size:.4f}")
        lines.append(f"- Significativo: {'✅ Sim' if stats.significant else '❌ Não'}")
        lines.append(f"- Pressupostos atendidos: {'✅' if stats.assumptions_met else '⚠️ Não'}\n")

        # Pressupostos
        if stats.assumptions:
            lines.append("**Pressupostos:**")
            for a in stats.assumptions:
                icon = "✅" if a.passed else "⚠️"
                lines.append(f"- {icon} {a.description}")
            lines.append("")

        # Post-hoc
        if stats.post_hoc:
            lines.append("**Comparações Post-hoc (Bonferroni):**")
            for ph in stats.post_hoc:
                icon = "✅" if ph.significant else "—"
                lines.append(f"- {icon} {ph.group1} vs {ph.group2}: "
                           f"p_adj = {ph.p_adjusted:.4f}")
            lines.append("")

        # Tabela descritiva
        if writing.table_text:
            lines.append("### Estatística Descritiva")
            lines.append(writing.table_text)
            lines.append("")

        # Figuras
        if figures:
            lines.append("### Figuras Geradas")
            for i, fig in enumerate(figures):
                lines.append(f"- **Fig {i+1}** ({fig.figure_type}): `{fig.file_path}`")
            lines.append("")

        # Legendas
        if writing.figure_legends:
            lines.append("### Legendas")
            for legend in writing.figure_legends:
                lines.append(f"- {legend}")
            lines.append("")

        # Texto de resultados
        lines.append("### Seção Resultados")
        llm_tag = " *(refinado via Ollama)*" if writing.llm_enhanced else ""
        lines.append(f"{writing.results_section}{llm_tag}\n")

        # Exportação
        if export.success:
            lines.append("### Arquivos Exportados")
            lines.append(f"- GraphPad Prism: `{export.pzfx_path}`")
            if export.csv_path:
                lines.append(f"- CSV: `{export.csv_path}`")

        # Warnings
        all_warnings = (data.warnings + cls.warnings +
                        stats.warnings + export.warnings)
        if all_warnings:
            lines.append("\n### ⚠️ Avisos")
            for w in all_warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)

    def _format_classification(self, cls) -> str:
        lines = [
            "## 🔬 Classificação do Experimento\n",
            f"**Tipo:** {cls.experiment_type.value}",
            f"**Variável:** {cls.variable_type.value}",
            f"**Grupos:** {cls.n_groups}",
            f"**Pareado:** {'Sim' if cls.is_paired else 'Não'}",
            f"**Confiança:** {cls.confidence:.0%}",
            f"**Justificativa:** {cls.reasoning}",
            f"\n**Testes sugeridos:** {', '.join(cls.suggested_tests)}",
        ]
        return "\n".join(lines)

    def _format_stats(self, stats) -> str:
        return stats.interpretation

    def _format_figures(self, figures) -> str:
        lines = ["## Figuras Geradas\n"]
        for i, f in enumerate(figures):
            lines.append(f"- Fig {i+1}: `{f.file_path}` ({f.figure_type})")
        return "\n".join(lines)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _extract_path(self, query: str) -> Optional[str]:
        """Extrai caminho de arquivo da query."""
        import re
        # Padrões comuns
        patterns = [
            r'["\']([^"\']+\.(?:xlsx|csv|xls|tsv))["\']',
            r'(\S+\.(?:xlsx|csv|xls|tsv))',
        ]
        for pat in patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _detect_mode(self, query: str) -> str:
        """Detecta modo parcial na query (ignora caminhos de arquivo)."""
        import re
        # Remover caminhos de arquivo antes da analise de modo
        q = re.sub(r'\S+\.(?:xlsx|csv|xls|tsv)', '', query).lower().strip()
        if any(w in q for w in ["classificar", "classify only", "detectar tipo", "only classify"]):
            return "classify_only"
        if any(w in q for w in ["estatistica apenas", "stats only", "only stats", "apenas teste"]):
            return "stats_only"
        if any(w in q for w in ["grafico apenas", "plot only", "only plot", "apenas figura"]):
            return "plot_only"
        return "full"

    def _help_text(self) -> str:
        return (
            "## Prism AI Copilot\n\n"
            "Analise cientifica automatizada. Forneca um arquivo de dados:\n\n"
            "**Uso:**\n"
            "- `prism analyze dados.xlsx` -- pipeline completo\n"
            "- `prism classify dados.csv` -- apenas classificacao\n"
            "- `prism stats dados.xlsx` -- apenas estatistica\n"
            "- `prism plot dados.xlsx` -- apenas graficos\n\n"
            "**Formatos aceitos:** .xlsx, .csv, .tsv\n\n"
            "**Contexto:** file_path, language (en/pt), alpha (0.05), dpi (300)"
        )
