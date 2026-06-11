"""
Prism AI — Statistical Decision Agent
=======================================
Seleciona, valida pressupostos e executa testes estatísticos.
Retorna resultados formatados com p-values, effect sizes e interpretação.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Any
from scipy import stats

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismStats")


@dataclass
class AssumptionResult:
    """Resultado de um teste de pressuposto."""
    test_name: str
    statistic: float
    p_value: float
    passed: bool
    description: str


@dataclass
class PostHocResult:
    """Resultado de comparação post-hoc."""
    group1: str
    group2: str
    statistic: float
    p_value: float
    p_adjusted: float
    significant: bool


@dataclass
class StatsResult:
    """Resultado completo da análise estatística."""
    test_name: str
    test_full_name: str
    statistic: float
    p_value: float
    effect_size: Optional[float]
    effect_size_name: Optional[str]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    df: Optional[float]
    assumptions: list[AssumptionResult]
    assumptions_met: bool
    post_hoc: list[PostHocResult]
    interpretation: str
    alpha: float = 0.05
    significant: bool = False
    warnings: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


class StatsAgent:
    """Seleciona e executa testes estatísticos com validação de pressupostos."""

    def run(self, ingested_data, classification, config: dict = None) -> StatsResult:
        """
        Pipeline estatístico completo.

        Args:
            ingested_data: IngestedData do IngestionAgent
            classification: ExperimentClassification do ClassificationAgent
            config: dict opcional com alpha, test_override, etc.

        Returns:
            StatsResult com teste, pressupostos, post-hoc e interpretação.
        """
        config = config or {}
        alpha = config.get("alpha", 0.05)
        d = ingested_data
        c = classification

        log.info(f"Análise estatística: {c.experiment_type.value} | "
                 f"Testes sugeridos: {c.suggested_tests}")

        # 1. Extrair grupos de dados
        groups_data = self._extract_groups(d)

        # 2. Testar pressupostos
        assumptions = self._test_assumptions(groups_data)
        assumptions_met = all(a.passed for a in assumptions)

        # 3. Selecionar teste
        test_name = config.get("test_override") or self._select_test(c, assumptions_met)

        # 4. Executar teste
        result = self._run_test(test_name, groups_data, alpha, d, c)
        result.assumptions = assumptions
        result.assumptions_met = assumptions_met

        # 5. Post-hoc (se aplicável)
        if result.significant and c.n_groups > 2 and test_name in ("one_way_anova", "kruskal_wallis"):
            result.post_hoc = self._run_post_hoc(test_name, groups_data, alpha)

        # 6. Interpretação
        result.interpretation = self._generate_interpretation(result, c)

        log.info(f"  Teste: {result.test_full_name} | p={result.p_value:.4f} | "
                 f"sig={result.significant}")
        return result

    # ── Extração de dados ────────────────────────────────────────────────

    def _extract_groups(self, data) -> dict[str, np.ndarray]:
        """Extrai arrays por grupo."""
        df = data.df
        gc = data.group_column
        vc = data.value_columns[0]  # Primeira variável
        groups = {}
        for grp in df[gc].unique():
            vals = df.loc[df[gc] == grp, vc].dropna().values.astype(float)
            groups[str(grp)] = vals
        return groups

    # ── Pressupostos ─────────────────────────────────────────────────────

    def _test_assumptions(self, groups: dict[str, np.ndarray]) -> list[AssumptionResult]:
        """Testa normalidade (Shapiro-Wilk) e homocedasticidade (Levene)."""
        results = []

        # Shapiro-Wilk por grupo
        for name, vals in groups.items():
            if len(vals) < 3:
                results.append(AssumptionResult(
                    test_name="shapiro_wilk",
                    statistic=float("nan"),
                    p_value=float("nan"),
                    passed=False,
                    description=f"Grupo '{name}': N < 3, impossível testar normalidade.",
                ))
                continue
            if len(vals) > 5000:
                vals_sample = np.random.choice(vals, 5000, replace=False)
            else:
                vals_sample = vals
            try:
                stat, p = stats.shapiro(vals_sample)
                results.append(AssumptionResult(
                    test_name="shapiro_wilk",
                    statistic=float(stat),
                    p_value=float(p),
                    passed=p > 0.05,
                    description=f"Grupo '{name}': W={stat:.4f}, p={p:.4f} "
                                f"({'normal' if p > 0.05 else 'não-normal'})",
                ))
            except Exception as e:
                results.append(AssumptionResult(
                    test_name="shapiro_wilk", statistic=0, p_value=0,
                    passed=False, description=f"Grupo '{name}': erro — {e}",
                ))

        # Levene (se ≥ 2 grupos)
        arrays = list(groups.values())
        if len(arrays) >= 2:
            valid = [a for a in arrays if len(a) >= 2]
            if len(valid) >= 2:
                try:
                    stat, p = stats.levene(*valid)
                    results.append(AssumptionResult(
                        test_name="levene",
                        statistic=float(stat),
                        p_value=float(p),
                        passed=p > 0.05,
                        description=f"Levene: F={stat:.4f}, p={p:.4f} "
                                    f"({'homocedástico' if p > 0.05 else 'heterocedástico'})",
                    ))
                except Exception as e:
                    results.append(AssumptionResult(
                        test_name="levene", statistic=0, p_value=0,
                        passed=False, description=f"Levene: erro — {e}",
                    ))

        return results

    # ── Seleção de teste ─────────────────────────────────────────────────

    def _select_test(self, classification, assumptions_met: bool) -> str:
        """Seleciona teste baseado no tipo de experimento e pressupostos."""
        suggested = classification.suggested_tests
        if not suggested:
            return "independent_ttest"

        if assumptions_met:
            # Usar teste paramétrico (primeiro da lista)
            return suggested[0]
        else:
            # Usar teste não-paramétrico (segundo da lista, se existir)
            return suggested[1] if len(suggested) > 1 else suggested[0]

    # ── Execução de testes ───────────────────────────────────────────────

    def _run_test(self, test_name: str, groups: dict, alpha: float,
                  data, classification) -> StatsResult:
        """Executa o teste estatístico selecionado."""
        arrays = list(groups.values())
        names = list(groups.keys())

        base = dict(
            test_name=test_name, alpha=alpha, assumptions=[], assumptions_met=True,
            post_hoc=[], interpretation="", warnings=[], raw_data={"groups": names},
        )

        if test_name == "independent_ttest":
            return self._independent_ttest(arrays, alpha, base)
        elif test_name == "paired_ttest":
            return self._paired_ttest(arrays, alpha, base)
        elif test_name == "mann_whitney":
            return self._mann_whitney(arrays, alpha, base)
        elif test_name == "wilcoxon_signed_rank":
            return self._wilcoxon(arrays, alpha, base)
        elif test_name == "one_way_anova":
            return self._one_way_anova(arrays, alpha, base)
        elif test_name == "kruskal_wallis":
            return self._kruskal_wallis(arrays, alpha, base)
        elif test_name == "pearson_correlation":
            return self._pearson(arrays, alpha, base, data)
        elif test_name == "spearman_correlation":
            return self._spearman(arrays, alpha, base, data)
        elif test_name == "one_sample_ttest":
            return self._one_sample_ttest(arrays, alpha, base)
        else:
            # Fallback inteligente: ANOVA se >2 grupos, t-test se 2
            if len(arrays) > 2:
                log.warning(f"Teste '{test_name}' não implementado, fallback para one-way ANOVA.")
                base["test_name"] = "one_way_anova"
                base["warnings"] = [f"Teste '{test_name}' não implementado — usando one-way ANOVA."]
                return self._one_way_anova(arrays, alpha, base)
            else:
                log.warning(f"Teste '{test_name}' não implementado, fallback para t-test.")
                base["test_name"] = "independent_ttest"
                base["warnings"] = [f"Teste '{test_name}' não implementado — usando t-test independente."]
                return self._independent_ttest(arrays, alpha, base)

    def _independent_ttest(self, arrays, alpha, base) -> StatsResult:
        a, b = arrays[0], arrays[1] if len(arrays) > 1 else arrays[0]
        stat, p = stats.ttest_ind(a, b)
        d_cohen = (a.mean() - b.mean()) / np.sqrt((a.std()**2 + b.std()**2) / 2)
        diff = a.mean() - b.mean()
        se = np.sqrt(a.std()**2/len(a) + b.std()**2/len(b))
        df_val = len(a) + len(b) - 2
        t_crit = stats.t.ppf(1 - alpha/2, df_val)
        return StatsResult(
            test_full_name="Independent samples t-test",
            statistic=float(stat), p_value=float(p),
            effect_size=float(abs(d_cohen)), effect_size_name="Cohen's d",
            ci_lower=float(diff - t_crit * se), ci_upper=float(diff + t_crit * se),
            df=float(df_val), significant=p < alpha, **base,
        )

    def _paired_ttest(self, arrays, alpha, base) -> StatsResult:
        a, b = arrays[0], arrays[1] if len(arrays) > 1 else arrays[0]
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
        stat, p = stats.ttest_rel(a, b)
        d_diff = a - b
        d_cohen = d_diff.mean() / d_diff.std() if d_diff.std() > 0 else 0
        return StatsResult(
            test_full_name="Paired samples t-test",
            statistic=float(stat), p_value=float(p),
            effect_size=float(abs(d_cohen)), effect_size_name="Cohen's d (paired)",
            ci_lower=None, ci_upper=None, df=float(n - 1),
            significant=p < alpha, **base,
        )

    def _mann_whitney(self, arrays, alpha, base) -> StatsResult:
        a, b = arrays[0], arrays[1] if len(arrays) > 1 else arrays[0]
        stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        n_total = len(a) + len(b)
        r = 1 - (2 * stat) / (len(a) * len(b))
        return StatsResult(
            test_full_name="Mann-Whitney U test",
            statistic=float(stat), p_value=float(p),
            effect_size=float(abs(r)), effect_size_name="rank-biserial r",
            ci_lower=None, ci_upper=None, df=None,
            significant=p < alpha, **base,
        )

    def _wilcoxon(self, arrays, alpha, base) -> StatsResult:
        a, b = arrays[0], arrays[1] if len(arrays) > 1 else arrays[0]
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
        stat, p = stats.wilcoxon(a, b)
        return StatsResult(
            test_full_name="Wilcoxon signed-rank test",
            statistic=float(stat), p_value=float(p),
            effect_size=None, effect_size_name=None,
            ci_lower=None, ci_upper=None, df=None,
            significant=p < alpha, **base,
        )

    def _one_way_anova(self, arrays, alpha, base) -> StatsResult:
        stat, p = stats.f_oneway(*arrays)
        # Eta-squared
        all_vals = np.concatenate(arrays)
        grand_mean = all_vals.mean()
        ss_between = sum(len(a) * (a.mean() - grand_mean)**2 for a in arrays)
        ss_total = np.sum((all_vals - grand_mean)**2)
        eta_sq = ss_between / ss_total if ss_total > 0 else 0
        df_between = len(arrays) - 1
        df_within = len(all_vals) - len(arrays)
        base_copy = {k: v for k, v in base.items() if k != "raw_data"}
        return StatsResult(
            test_full_name="One-way ANOVA",
            statistic=float(stat), p_value=float(p),
            effect_size=float(eta_sq), effect_size_name="eta-squared",
            ci_lower=None, ci_upper=None,
            df=float(df_between),
            significant=p < alpha, **base_copy,
            raw_data={**base.get("raw_data", {}),
                      "df_between": df_between, "df_within": df_within},
        )

    def _kruskal_wallis(self, arrays, alpha, base) -> StatsResult:
        stat, p = stats.kruskal(*arrays)
        n_total = sum(len(a) for a in arrays)
        epsilon_sq = (stat - len(arrays) + 1) / (n_total - len(arrays))
        return StatsResult(
            test_full_name="Kruskal-Wallis H test",
            statistic=float(stat), p_value=float(p),
            effect_size=float(max(0, epsilon_sq)), effect_size_name="ε² (epsilon-squared)",
            ci_lower=None, ci_upper=None, df=float(len(arrays) - 1),
            significant=p < alpha, **base,
        )

    def _pearson(self, arrays, alpha, base, data) -> StatsResult:
        df = data.df
        cols = data.value_columns[:2]
        x, y = df[cols[0]].dropna().values, df[cols[1]].dropna().values
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        r, p = stats.pearsonr(x, y)
        return StatsResult(
            test_full_name="Pearson correlation",
            statistic=float(r), p_value=float(p),
            effect_size=float(r**2), effect_size_name="R²",
            ci_lower=None, ci_upper=None, df=float(n - 2),
            significant=p < alpha, **base,
        )

    def _spearman(self, arrays, alpha, base, data) -> StatsResult:
        df = data.df
        cols = data.value_columns[:2]
        x, y = df[cols[0]].dropna().values, df[cols[1]].dropna().values
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        rho, p = stats.spearmanr(x, y)
        return StatsResult(
            test_full_name="Spearman rank correlation",
            statistic=float(rho), p_value=float(p),
            effect_size=float(rho**2), effect_size_name="ρ²",
            ci_lower=None, ci_upper=None, df=float(n - 2),
            significant=p < alpha, **base,
        )

    def _one_sample_ttest(self, arrays, alpha, base) -> StatsResult:
        a = arrays[0]
        stat, p = stats.ttest_1samp(a, 0)
        d = a.mean() / a.std() if a.std() > 0 else 0
        return StatsResult(
            test_full_name="One-sample t-test (μ₀ = 0)",
            statistic=float(stat), p_value=float(p),
            effect_size=float(abs(d)), effect_size_name="Cohen's d",
            ci_lower=None, ci_upper=None, df=float(len(a) - 1),
            significant=p < alpha, **base,
        )

    # ── Post-hoc ─────────────────────────────────────────────────────────

    def _run_post_hoc(self, test_name: str, groups: dict, alpha: float) -> list[PostHocResult]:
        """Comparações post-hoc com correção de Bonferroni."""
        names = list(groups.keys())
        arrays = list(groups.values())
        results = []
        n_comparisons = len(names) * (len(names) - 1) // 2

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if test_name == "one_way_anova":
                    stat, p = stats.ttest_ind(arrays[i], arrays[j])
                else:
                    stat, p = stats.mannwhitneyu(arrays[i], arrays[j], alternative="two-sided")

                p_adj = min(p * n_comparisons, 1.0)  # Bonferroni
                results.append(PostHocResult(
                    group1=names[i], group2=names[j],
                    statistic=float(stat), p_value=float(p),
                    p_adjusted=float(p_adj),
                    significant=p_adj < alpha,
                ))

        return results

    # ── Interpretação ────────────────────────────────────────────────────

    def _generate_interpretation(self, result, classification) -> str:
        """Gera interpretacao textual do resultado."""
        sig = "significativa" if result.significant else "nao significativa"
        p_str = f"p = {result.p_value:.4f}" if result.p_value >= 0.001 else "p < 0.001"

        text = (
            f"O {result.test_full_name} revelou diferenca estatisticamente {sig} "
            f"({p_str}, alpha = {result.alpha})."
        )

        if result.effect_size is not None:
            text += f" O tamanho de efeito foi {result.effect_size_name} = {result.effect_size:.3f}"
            if result.effect_size_name and "cohen" in result.effect_size_name.lower():
                es = abs(result.effect_size)
                if es < 0.2:
                    text += " (negligivel)."
                elif es < 0.5:
                    text += " (pequeno)."
                elif es < 0.8:
                    text += " (medio)."
                else:
                    text += " (grande)."
            else:
                text += "."

        if not result.assumptions_met:
            text += (" Os pressupostos de normalidade e/ou homocedasticidade "
                     "nao foram atendidos; teste nao-parametrico recomendado.")

        return text
