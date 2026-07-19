"""
Prism AI — Experiment Classification Agent
============================================
Classifica o tipo de experimento a partir dos dados ingeridos:
  - comparação simples (2 grupos)
  - múltiplos grupos (>2 grupos)
  - medidas repetidas
  - série temporal
  - correlação
  - dose-resposta
"""

from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismClassification")


class ExperimentType(str, Enum):
    """Tipos de experimento detectáveis."""
    TWO_GROUP = "two_group_comparison"
    MULTI_GROUP = "multi_group_comparison"
    REPEATED_MEASURES = "repeated_measures"
    TIME_SERIES = "time_series"
    CORRELATION = "correlation"
    DOSE_RESPONSE = "dose_response"
    ONE_SAMPLE = "one_sample"
    PAIRED = "paired_comparison"


class VariableType(str, Enum):
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"
    COUNT = "count"
    PROPORTION = "proportion"


@dataclass
class ExperimentClassification:
    """Resultado da classificação do experimento."""
    experiment_type: ExperimentType
    variable_type: VariableType
    n_groups: int
    n_variables: int
    is_paired: bool
    has_timepoints: bool
    confidence: float  # 0.0 – 1.0
    reasoning: str
    suggested_tests: list[str]
    warnings: list[str]


class ClassificationAgent:
    """Classifica o tipo de experimento por heurísticas determinísticas."""

    def run(self, ingested_data) -> ExperimentClassification:
        """
        Classifica o experimento com base nos dados ingeridos.

        Args:
            ingested_data: IngestedData do IngestionAgent

        Returns:
            ExperimentClassification com tipo, variáveis e testes sugeridos.
        """
        d = ingested_data
        log.info(f"Classificando: {d.n_groups} grupos, {len(d.value_columns)} variáveis, "
                 f"pareado={d.is_paired}, temporal={d.has_timepoints}")

        # Detectar tipo de variável
        var_type = self._classify_variable_type(d)

        # Classificar experimento
        exp_type, confidence, reasoning = self._classify_experiment(d)

        # Sugerir testes
        suggested = self._suggest_tests(exp_type, var_type, d)

        warnings = []
        if confidence < 0.6:
            warnings.append(
                "Classificação com baixa confiança — considere especificar "
                "manualmente o tipo de experimento."
            )

        result = ExperimentClassification(
            experiment_type=exp_type,
            variable_type=var_type,
            n_groups=d.n_groups,
            n_variables=len(d.value_columns),
            is_paired=d.is_paired,
            has_timepoints=d.has_timepoints,
            confidence=confidence,
            reasoning=reasoning,
            suggested_tests=suggested,
            warnings=warnings,
        )

        log.info(f"  Tipo: {exp_type.value} | Variável: {var_type.value} | "
                 f"Confiança: {confidence:.0%}")
        return result

    # ── Classificação de variável ────────────────────────────────────────

    def _classify_variable_type(self, data) -> VariableType:
        """Determina o tipo predominante das variáveis numéricas."""
        import pandas as pd
        import numpy as np

        df = data.df
        for col in data.value_columns:
            vals = df[col].dropna()
            if len(vals) == 0:
                continue

            # Proporções (0-1 ou 0-100)
            if vals.min() >= 0 and vals.max() <= 1:
                return VariableType.PROPORTION
            if vals.min() >= 0 and vals.max() <= 100 and vals.mean() > 10:
                # Pode ser percentual
                all_int = (vals == vals.astype(int)).all()
                if not all_int:
                    return VariableType.PROPORTION

            # Contagens (inteiros não-negativos)
            if vals.min() >= 0 and (vals == vals.astype(int)).all():
                if vals.max() < 100:
                    return VariableType.COUNT

        return VariableType.CONTINUOUS

    # ── Classificação de experimento ─────────────────────────────────────

    def _classify_experiment(self, data) -> tuple[ExperimentType, float, str]:
        """
        Classifica o tipo de experimento.
        Returns: (ExperimentType, confidence, reasoning)
        """
        n = data.n_groups
        paired = data.is_paired
        temporal = data.has_timepoints
        n_vars = len(data.value_columns)

        # Série temporal
        if temporal:
            if n <= 1:
                return (ExperimentType.TIME_SERIES, 0.9,
                        f"Dados com coluna temporal detectada, {n} grupo(s).")
            return (ExperimentType.REPEATED_MEASURES, 0.85,
                    f"Dados com coluna temporal e {n} grupos → medidas repetidas.")

        # Um grupo
        if n <= 1:
            if n_vars >= 2:
                return (ExperimentType.CORRELATION, 0.75,
                        f"1 grupo com {n_vars} variáveis numéricas → correlação.")
            return (ExperimentType.ONE_SAMPLE, 0.8,
                    "1 grupo, 1 variável → teste de uma amostra.")

        # Dois grupos
        if n == 2:
            if paired:
                return (ExperimentType.PAIRED, 0.85,
                        "2 grupos com N igual → comparação pareada.")
            return (ExperimentType.TWO_GROUP, 0.9,
                    "2 grupos independentes → comparação simples.")

        # Múltiplos grupos
        if n > 2:
            # Checar se os nomes dos grupos sugerem dose-resposta
            groups = data.metadata.get("groups", [])
            if self._looks_like_dose_response(groups):
                return (ExperimentType.DOSE_RESPONSE, 0.8,
                        f"{n} grupos com padrão dose-resposta.")

            if paired:
                return (ExperimentType.REPEATED_MEASURES, 0.8,
                        f"{n} grupos pareados → medidas repetidas.")

            return (ExperimentType.MULTI_GROUP, 0.9,
                    f"{n} grupos independentes → comparação múltipla.")

        return (ExperimentType.MULTI_GROUP, 0.5,
                "Classificação fallback — estrutura não clara.")

    def _looks_like_dose_response(self, groups: list) -> bool:
        """Verifica se os nomes dos grupos sugerem dose-resposta."""
        import re
        numeric_count = 0
        for g in groups:
            g_str = str(g)
            # Detecta padrões como "10mg", "100uM", "0.1", etc.
            if re.match(r"^\d+(\.\d+)?\s*(mg|ug|µg|nm|um|µm|mm|ml|ul|µl|%|x)?$",
                        g_str, re.IGNORECASE):
                numeric_count += 1
        return numeric_count >= len(groups) * 0.6

    # ── Sugestão de testes ───────────────────────────────────────────────

    def _suggest_tests(self, exp_type: ExperimentType, var_type: VariableType,
                       data) -> list[str]:
        """Sugere testes estatísticos baseado no tipo de experimento."""
        tests = []

        if exp_type == ExperimentType.ONE_SAMPLE:
            tests = ["one_sample_ttest", "wilcoxon_signed_rank"]

        elif exp_type == ExperimentType.TWO_GROUP:
            tests = ["independent_ttest", "mann_whitney"]

        elif exp_type == ExperimentType.PAIRED:
            tests = ["paired_ttest", "wilcoxon_signed_rank"]

        elif exp_type == ExperimentType.MULTI_GROUP:
            tests = ["one_way_anova", "kruskal_wallis"]

        elif exp_type == ExperimentType.REPEATED_MEASURES:
            tests = ["repeated_measures_anova", "friedman"]

        elif exp_type == ExperimentType.TIME_SERIES:
            tests = ["repeated_measures_anova", "linear_mixed_model"]

        elif exp_type == ExperimentType.CORRELATION:
            tests = ["pearson_correlation", "spearman_correlation"]

        elif exp_type == ExperimentType.DOSE_RESPONSE:
            tests = ["one_way_anova", "linear_regression", "kruskal_wallis"]

        return tests
