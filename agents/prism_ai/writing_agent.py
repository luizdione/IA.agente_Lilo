"""
Prism AI — Scientific Writing Agent
=====================================
Gera texto da seção "Resultados" em linguagem científica.
Usa Ollama (modelo local) para refinamento, mas produz uma versão
determinística como fallback.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismWriting")


@dataclass
class WritingResult:
    """Resultado da geração de texto científico."""
    results_section: str
    figure_legends: list[str]
    table_text: Optional[str]
    language: str  # "pt" ou "en"
    llm_enhanced: bool  # True se refinado via Ollama


class WritingAgent:
    """Gera texto científico para seção Resultados."""

    def run(self, ingested_data, classification, stats_result,
            figures: list, config: dict = None) -> WritingResult:
        """
        Gera seção Resultados completa.

        Args:
            ingested_data: IngestedData
            classification: ExperimentClassification
            stats_result: StatsResult
            figures: lista de FigureResult
            config: dict com language, enhance_with_llm, etc.

        Returns:
            WritingResult com texto e legendas.
        """
        config = config or {}
        lang = config.get("language", "en")
        use_llm = config.get("enhance_with_llm", True)

        log.info(f"Gerando texto científico (lang={lang}, llm={use_llm})")

        # 1. Gerar texto determinístico
        text = self._generate_deterministic(ingested_data, classification,
                                             stats_result, lang)

        # 2. Gerar legendas
        legends = self._generate_legends(figures, stats_result, lang)

        # 3. Tabela descritiva
        table_text = self._generate_descriptive_table(ingested_data, lang)

        # 4. Refinar com Ollama (se disponível)
        llm_enhanced = False
        if use_llm:
            enhanced = self._enhance_with_ollama(text, lang)
            if enhanced:
                text = enhanced
                llm_enhanced = True

        return WritingResult(
            results_section=text,
            figure_legends=legends,
            table_text=table_text,
            language=lang,
            llm_enhanced=llm_enhanced,
        )

    # ── Geração determinística ───────────────────────────────────────────

    def _generate_deterministic(self, data, classification, stats, lang) -> str:
        """Gera texto de resultados sem LLM."""
        c = classification
        s = stats
        d = data

        if lang == "pt":
            return self._generate_pt(d, c, s)
        return self._generate_en(d, c, s)

    def _generate_en(self, data, classification, stats) -> str:
        c = classification
        s = stats
        n_total = sum(data.n_samples_per_group.values())
        groups_str = ", ".join(
            f"{g} (n = {n})" for g, n in data.n_samples_per_group.items()
        )

        # Parágrafo descritivo
        desc = (
            f"A total of {n_total} observations were analyzed across "
            f"{c.n_groups} group(s): {groups_str}. "
        )

        # Pressupostos
        norm_results = [a for a in s.assumptions if a.test_name == "shapiro_wilk"]
        levene_results = [a for a in s.assumptions if a.test_name == "levene"]

        if norm_results:
            all_normal = all(a.passed for a in norm_results)
            if all_normal:
                desc += "Data were normally distributed (Shapiro-Wilk test, all p > 0.05). "
            else:
                non_normal = [a for a in norm_results if not a.passed]
                desc += (
                    f"Normality was violated in {len(non_normal)} group(s) "
                    f"(Shapiro-Wilk test, p < 0.05). "
                )

        if levene_results:
            lev = levene_results[0]
            if lev.passed:
                desc += f"Homogeneity of variances was confirmed (Levene's test, F = {lev.statistic:.2f}, p = {lev.p_value:.3f}). "
            else:
                desc += f"Variances were heterogeneous (Levene's test, F = {lev.statistic:.2f}, p = {lev.p_value:.3f}). "

        # Resultado do teste
        p_str = f"p = {s.p_value:.4f}" if s.p_value >= 0.001 else "p < 0.001"
        sig_word = "significant" if s.significant else "not significant"

        result = (
            f"The {s.test_full_name} revealed a statistically {sig_word} "
            f"difference ({s.test_name.replace('_', ' ')}: "
        )

        if s.df is not None:
            if "anova" in s.test_name.lower() or "f_oneway" in s.test_name:
                df_b = s.raw_data.get("df_between", s.df)
                df_w = s.raw_data.get("df_within", "")
                result += f"F({df_b}, {df_w}) = {s.statistic:.3f}, {p_str}"
            elif "t" in s.test_name:
                result += f"t({s.df:.0f}) = {s.statistic:.3f}, {p_str}"
            else:
                result += f"H = {s.statistic:.3f}, df = {s.df:.0f}, {p_str}"
        else:
            result += f"U = {s.statistic:.3f}, {p_str}"

        result += "). "

        # Effect size
        if s.effect_size is not None:
            result += f"The effect size was {s.effect_size_name} = {s.effect_size:.3f}. "

        # Post-hoc
        if s.post_hoc:
            sig_pairs = [ph for ph in s.post_hoc if ph.significant]
            if sig_pairs:
                pairs_str = "; ".join(
                    f"{ph.group1} vs. {ph.group2} (p = {ph.p_adjusted:.4f})"
                    for ph in sig_pairs
                )
                result += f"Post-hoc pairwise comparisons (Bonferroni-corrected) indicated significant differences between: {pairs_str}. "

        return desc + "\n\n" + result

    def _generate_pt(self, data, classification, stats) -> str:
        c = classification
        s = stats
        n_total = sum(data.n_samples_per_group.values())
        groups_str = ", ".join(
            f"{g} (n = {n})" for g, n in data.n_samples_per_group.items()
        )

        desc = (
            f"Um total de {n_total} observações foram analisadas em "
            f"{c.n_groups} grupo(s): {groups_str}. "
        )

        norm_results = [a for a in s.assumptions if a.test_name == "shapiro_wilk"]
        if norm_results:
            all_normal = all(a.passed for a in norm_results)
            if all_normal:
                desc += "Os dados apresentaram distribuição normal (teste de Shapiro-Wilk, todos p > 0,05). "
            else:
                desc += "A normalidade foi violada em parte dos grupos (Shapiro-Wilk, p < 0,05). "

        p_str = f"p = {s.p_value:.4f}" if s.p_value >= 0.001 else "p < 0,001"
        sig_word = "significativa" if s.significant else "não significativa"

        result = (
            f"O {s.test_full_name} revelou diferença estatisticamente {sig_word} "
            f"({p_str}). "
        )

        if s.effect_size is not None:
            result += f"O tamanho de efeito foi {s.effect_size_name} = {s.effect_size:.3f}. "

        if s.post_hoc:
            sig_pairs = [ph for ph in s.post_hoc if ph.significant]
            if sig_pairs:
                pairs_str = "; ".join(
                    f"{ph.group1} vs. {ph.group2} (p = {ph.p_adjusted:.4f})"
                    for ph in sig_pairs
                )
                result += f"Comparações post-hoc (Bonferroni) indicaram diferenças significativas entre: {pairs_str}. "

        return desc + "\n\n" + result

    # ── Legendas ─────────────────────────────────────────────────────────

    def _generate_legends(self, figures, stats, lang) -> list[str]:
        legends = []
        for i, fig in enumerate(figures):
            if lang == "pt":
                legend = f"Figura {i+1}. {fig.description}"
                if stats.significant:
                    legend += f" *p < 0,05, **p < 0,01, ***p < 0,001."
            else:
                legend = f"Figure {i+1}. {fig.description}"
                if stats.significant:
                    legend += f" *p < 0.05, **p < 0.01, ***p < 0.001."
            legends.append(legend)
        return legends

    # ── Tabela descritiva ────────────────────────────────────────────────

    def _generate_descriptive_table(self, data, lang) -> str:
        import pandas as pd

        df = data.df
        gc = data.group_column
        vc = data.value_columns[0]

        rows = []
        for grp in df[gc].unique():
            vals = df.loc[df[gc] == grp, vc].dropna()
            rows.append({
                "Group" if lang == "en" else "Grupo": str(grp),
                "N": len(vals),
                "Mean" if lang == "en" else "Média": f"{vals.mean():.3f}",
                "SD" if lang == "en" else "DP": f"{vals.std():.3f}",
                "SEM": f"{vals.sem():.3f}",
                "Min": f"{vals.min():.3f}",
                "Max": f"{vals.max():.3f}",
                "Median" if lang == "en" else "Mediana": f"{vals.median():.3f}",
            })

        table_df = pd.DataFrame(rows)
        return table_df.to_markdown(index=False)

    # ── Ollama enhancement ───────────────────────────────────────────────

    def _enhance_with_ollama(self, text: str, lang: str) -> Optional[str]:
        """Tenta refinar texto usando Ollama local."""
        try:
            from shared.llm_client import LLMClient
            client = LLMClient()

            if lang == "pt":
                prompt = (
                    "Refine o seguinte texto de resultados científicos para um artigo acadêmico. "
                    "Mantenha todos os valores estatísticos exatos. Melhore apenas a fluência "
                    "e o estilo. Retorne APENAS o texto refinado, sem explicações.\n\n"
                    f"{text}"
                )
            else:
                prompt = (
                    "Refine the following scientific results text for a peer-reviewed journal. "
                    "Keep all statistical values exact. Improve only fluency and style. "
                    "Return ONLY the refined text, no explanations.\n\n"
                    f"{text}"
                )

            response = client.generate(prompt, max_tokens=2000)
            if response and len(response) > len(text) * 0.5:
                log.info("  Texto refinado via Ollama.")
                return response
        except Exception as e:
            log.warning(f"  Ollama não disponível para refinamento: {e}")
        return None
