"""
Prism AI — Visualization Agent
================================
Gera gráficos padrão publicação científica (≥300 dpi).
Compatível com estilo GraphPad Prism.
"""

import numpy as np
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismVisualization")


@dataclass
class FigureResult:
    """Metadados de uma figura gerada."""
    file_path: str
    figure_type: str
    title: str
    width_inches: float
    height_inches: float
    dpi: int
    description: str


class VisualizationAgent:
    """Gera gráficos no padrão de publicação científica."""

    # Paleta GraphPad Prism clássica
    PRISM_COLORS = [
        "#000000",  # preto
        "#E64B35",  # vermelho
        "#4DBBD5",  # azul claro
        "#00A087",  # verde
        "#3C5488",  # azul escuro
        "#F39B7F",  # salmão
        "#8491B4",  # cinza-azul
        "#91D1C2",  # menta
        "#DC9100",  # laranja
        "#7E6148",  # marrom
    ]

    def run(self, ingested_data, classification, stats_result,
            output_dir: str, config: dict = None) -> list[FigureResult]:
        """
        Gera figuras automaticamente baseadas no tipo de experimento.

        Args:
            ingested_data: IngestedData
            classification: ExperimentClassification
            stats_result: StatsResult
            output_dir: diretório para salvar figuras
            config: dict com dpi, figsize, style, etc.

        Returns:
            Lista de FigureResult com caminhos e metadados.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        config = config or {}
        dpi = config.get("dpi", 300)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Estilo publicação
        self._set_publication_style()

        figures = []
        exp_type = classification.experiment_type.value

        d = ingested_data
        df = d.df
        gc = d.group_column
        vc = d.value_columns[0]

        # 1. Gráfico principal baseado no tipo
        if exp_type in ("two_group_comparison", "paired_comparison"):
            fig = self._plot_two_groups(df, gc, vc, stats_result, d.is_paired, config)
            fpath = str(out / "boxplot_comparison.png")
            fig.savefig(fpath, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            figures.append(FigureResult(
                file_path=fpath, figure_type="boxplot_with_points",
                title="Group Comparison", width_inches=4, height_inches=5,
                dpi=dpi, description="Boxplot com pontos individuais e significância.",
            ))

        elif exp_type in ("multi_group_comparison", "dose_response"):
            fig = self._plot_multi_groups(df, gc, vc, stats_result, config)
            fpath = str(out / "boxplot_multigroup.png")
            fig.savefig(fpath, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            figures.append(FigureResult(
                file_path=fpath, figure_type="boxplot_multigroup",
                title="Multi-Group Comparison", width_inches=6, height_inches=5,
                dpi=dpi, description="Boxplot múltiplos grupos com pontos e post-hoc.",
            ))

        elif exp_type == "correlation":
            if len(d.value_columns) >= 2:
                fig = self._plot_scatter(df, d.value_columns[0], d.value_columns[1],
                                         stats_result, config)
                fpath = str(out / "scatter_correlation.png")
                fig.savefig(fpath, dpi=dpi, bbox_inches="tight", facecolor="white")
                plt.close(fig)
                figures.append(FigureResult(
                    file_path=fpath, figure_type="scatter",
                    title="Correlation", width_inches=5, height_inches=5,
                    dpi=dpi, description="Scatter plot com linha de regressão.",
                ))

        elif exp_type in ("time_series", "repeated_measures"):
            fig = self._plot_time_series(df, gc, vc, d.timepoint_column, config)
            fpath = str(out / "timeseries.png")
            fig.savefig(fpath, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            figures.append(FigureResult(
                file_path=fpath, figure_type="line_plot",
                title="Time Series", width_inches=6, height_inches=4,
                dpi=dpi, description="Série temporal com erro padrão.",
            ))

        else:
            # Fallback: barplot com erro
            fig = self._plot_barplot(df, gc, vc, stats_result, config)
            fpath = str(out / "barplot.png")
            fig.savefig(fpath, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            figures.append(FigureResult(
                file_path=fpath, figure_type="barplot",
                title="Bar Plot", width_inches=5, height_inches=5,
                dpi=dpi, description="Barplot com barras de erro (SEM).",
            ))

        log.info(f"  Figuras geradas: {len(figures)}")
        return figures

    # ── Estilo ───────────────────────────────────────────────────────────

    def _set_publication_style(self):
        import matplotlib.pyplot as plt
        plt.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 1.0,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
        })

    # ── Plots ────────────────────────────────────────────────────────────

    def _plot_two_groups(self, df, gc, vc, stats, is_paired, config):
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=(4, 5))
        groups = df[gc].unique()
        colors = self.PRISM_COLORS[:2]

        # Boxplot
        bp = ax.boxplot(
            [df.loc[df[gc] == g, vc].dropna().values for g in groups],
            labels=groups, widths=0.5, patch_artist=True,
            boxprops=dict(linewidth=1),
            medianprops=dict(color="black", linewidth=1.5),
            whiskerprops=dict(linewidth=1),
            capprops=dict(linewidth=1),
        )
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.3)

        # Pontos individuais (jitter)
        for i, g in enumerate(groups):
            vals = df.loc[df[gc] == g, vc].dropna().values
            x = np.random.normal(i + 1, 0.04, len(vals))
            ax.scatter(x, vals, color=colors[i], s=25, alpha=0.7, edgecolors="none", zorder=3)

        # Linhas pareadas
        if is_paired:
            g1, g2 = groups[:2]
            v1 = df.loc[df[gc] == g1, vc].dropna().values
            v2 = df.loc[df[gc] == g2, vc].dropna().values
            n = min(len(v1), len(v2))
            for k in range(n):
                ax.plot([1, 2], [v1[k], v2[k]], color="gray", alpha=0.3, linewidth=0.5)

        # Significância
        if stats.significant:
            y_max = df[vc].max()
            y_range = df[vc].max() - df[vc].min()
            bar_y = y_max + y_range * 0.08
            ax.plot([1, 1, 2, 2], [bar_y, bar_y + y_range * 0.02,
                     bar_y + y_range * 0.02, bar_y], color="black", linewidth=1)
            p_text = self._p_stars(stats.p_value)
            ax.text(1.5, bar_y + y_range * 0.03, p_text, ha="center", fontsize=11)

        ax.set_ylabel(vc)
        ax.set_title("")
        fig.tight_layout()
        return fig

    def _plot_multi_groups(self, df, gc, vc, stats, config):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(max(6, len(df[gc].unique()) * 1.2), 5))
        groups = df[gc].unique()
        n_groups = len(groups)
        colors = self.PRISM_COLORS[:n_groups]

        bp = ax.boxplot(
            [df.loc[df[gc] == g, vc].dropna().values for g in groups],
            labels=groups, widths=0.5, patch_artist=True,
            medianprops=dict(color="black", linewidth=1.5),
        )
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.3)

        for i, g in enumerate(groups):
            vals = df.loc[df[gc] == g, vc].dropna().values
            x = np.random.normal(i + 1, 0.04, len(vals))
            ax.scatter(x, vals, color=colors[i], s=20, alpha=0.7, edgecolors="none", zorder=3)

        # Post-hoc brackets
        if stats.post_hoc:
            y_max = df[vc].max()
            y_range = df[vc].max() - df[vc].min()
            offset = 0
            group_list = list(groups)
            for ph in stats.post_hoc:
                if ph.significant:
                    i1 = group_list.index(ph.group1) + 1
                    i2 = group_list.index(ph.group2) + 1
                    bar_y = y_max + y_range * (0.08 + offset * 0.1)
                    ax.plot([i1, i1, i2, i2],
                            [bar_y, bar_y + y_range * 0.02,
                             bar_y + y_range * 0.02, bar_y],
                            color="black", linewidth=0.8)
                    ax.text((i1 + i2) / 2, bar_y + y_range * 0.025,
                            self._p_stars(ph.p_adjusted), ha="center", fontsize=9)
                    offset += 1

        ax.set_ylabel(vc)
        fig.tight_layout()
        return fig

    def _plot_scatter(self, df, col_x, col_y, stats, config):
        import matplotlib.pyplot as plt
        from scipy.stats import linregress

        fig, ax = plt.subplots(figsize=(5, 5))
        x = df[col_x].dropna().values
        y = df[col_y].dropna().values
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]

        ax.scatter(x, y, color=self.PRISM_COLORS[3], s=30, alpha=0.7, edgecolors="none")

        # Linha de regressão
        slope, intercept, r, p, se = linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, slope * x_line + intercept, color=self.PRISM_COLORS[1],
                linewidth=1.5, linestyle="--")

        # Anotação
        ax.text(0.05, 0.95, f"r = {r:.3f}\np = {p:.4f}",
                transform=ax.transAxes, va="top", fontsize=9,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)
        fig.tight_layout()
        return fig

    def _plot_time_series(self, df, gc, vc, time_col, config):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4))
        groups = df[gc].unique() if gc else ["all"]

        for i, g in enumerate(groups):
            subset = df[df[gc] == g] if gc else df
            if time_col:
                grouped = subset.groupby(time_col)[vc].agg(["mean", "sem"])
                ax.errorbar(grouped.index, grouped["mean"], yerr=grouped["sem"],
                            color=self.PRISM_COLORS[i], marker="o", markersize=4,
                            capsize=3, linewidth=1.5, label=str(g))
            else:
                ax.plot(subset[vc].values, color=self.PRISM_COLORS[i],
                        marker="o", markersize=3, linewidth=1.5, label=str(g))

        ax.set_xlabel(time_col or "Index")
        ax.set_ylabel(vc)
        if len(groups) > 1:
            ax.legend(frameon=False)
        fig.tight_layout()
        return fig

    def _plot_barplot(self, df, gc, vc, stats, config):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5, 5))
        groups = df[gc].unique()
        means = [df.loc[df[gc] == g, vc].mean() for g in groups]
        sems = [df.loc[df[gc] == g, vc].sem() for g in groups]
        x = np.arange(len(groups))
        colors = self.PRISM_COLORS[:len(groups)]

        ax.bar(x, means, yerr=sems, width=0.6, capsize=4,
                      color=colors, alpha=0.7, edgecolor="black", linewidth=0.8,
                      error_kw=dict(linewidth=1))

        # Pontos individuais
        for i, g in enumerate(groups):
            vals = df.loc[df[gc] == g, vc].dropna().values
            jitter = np.random.normal(i, 0.06, len(vals))
            ax.scatter(jitter, vals, color="black", s=15, alpha=0.5, zorder=3)

        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.set_ylabel(vc)
        fig.tight_layout()
        return fig

    # ── Helpers ──────────────────────────────────────────────────────────

    def _p_stars(self, p: float) -> str:
        if p < 0.001:
            return "***"
        elif p < 0.01:
            return "**"
        elif p < 0.05:
            return "*"
        return "ns"
