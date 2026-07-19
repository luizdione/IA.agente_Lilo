"""
Prism AI — Data Ingestion Agent
================================
Lê arquivos .xlsx/.csv, padroniza em tidy format,
valida consistência e retorna DataFrame limpo + metadados.
"""

import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismIngestion")


@dataclass
class IngestedData:
    """Container para dados ingeridos e padronizados."""
    df: pd.DataFrame
    n_groups: int
    n_samples_per_group: dict[str, int]
    group_column: str
    value_columns: list[str]
    is_paired: bool
    has_timepoints: bool
    timepoint_column: Optional[str]
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class IngestionAgent:
    """Lê, valida e padroniza dados experimentais."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}

    def run(self, file_path: str, config: dict = None) -> IngestedData:
        """
        Pipeline completo de ingestão.

        Args:
            file_path: caminho do arquivo de dados
            config: dict opcional com:
                - sheet_name: nome/índice da planilha (Excel)
                - separator: separador CSV (auto-detect se omitido)
                - group_col: nome explícito da coluna de grupos
                - value_cols: lista explícita de colunas numéricas

        Returns:
            IngestedData com DataFrame padronizado e metadados.
        """
        config = config or {}
        path = Path(file_path)
        log.info(f"Ingerindo: {path.name}")

        # 1. Leitura
        df = self._read_file(path, config)
        log.info(f"  Shape bruto: {df.shape}")

        # 2. Limpeza básica
        df = self._clean(df)

        # 3. Detecção de estrutura
        group_col = config.get("group_col") or self._detect_group_column(df)
        value_cols = config.get("value_cols") or self._detect_value_columns(df, group_col)
        timepoint_col = self._detect_timepoint_column(df, group_col, value_cols)

        warnings = []
        if not group_col:
            # Sem coluna de grupo — tratar colunas como grupos (wide format)
            df, group_col, value_cols = self._wide_to_tidy(df)
            warnings.append("Dados em formato wide — convertidos para tidy format.")

        # 4. Validação
        val_warnings = self._validate(df, group_col, value_cols)
        warnings.extend(val_warnings)

        # 5. Metadados
        groups = df[group_col].unique().tolist() if group_col else ["all"]
        n_per_group = {
            str(g): int(df[df[group_col] == g].shape[0])
            for g in groups
        } if group_col else {"all": len(df)}

        is_paired = self._detect_paired(df, group_col, n_per_group)
        has_timepoints = timepoint_col is not None

        result = IngestedData(
            df=df,
            n_groups=len(groups),
            n_samples_per_group=n_per_group,
            group_column=group_col or "group",
            value_columns=value_cols,
            is_paired=is_paired,
            has_timepoints=has_timepoints,
            timepoint_column=timepoint_col,
            warnings=warnings,
            metadata={
                "source_file": str(path),
                "original_shape": df.shape,
                "groups": groups,
                "dtypes": {c: str(df[c].dtype) for c in value_cols},
            },
        )

        log.info(f"  Grupos: {len(groups)} | Colunas numéricas: {len(value_cols)} | Pareado: {is_paired}")
        return result

    # ── Leitura ──────────────────────────────────────────────────────────

    def _read_file(self, path: Path, config: dict) -> pd.DataFrame:
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato não suportado: {ext}. Use: {self.SUPPORTED_EXTENSIONS}")

        if ext in (".xlsx", ".xls"):
            sheet = config.get("sheet_name", 0)
            return pd.read_excel(path, sheet_name=sheet)
        elif ext == ".tsv":
            return pd.read_csv(path, sep="\t")
        else:
            # Auto-detect separator
            sep = config.get("separator")
            if not sep:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    sample = f.read(2048)
                if sample.count("\t") > sample.count(","):
                    sep = "\t"
                elif sample.count(";") > sample.count(","):
                    sep = ";"
                else:
                    sep = ","
            return pd.read_csv(path, sep=sep)

    # ── Limpeza ──────────────────────────────────────────────────────────

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        # Remover colunas totalmente vazias
        df = df.dropna(axis=1, how="all")
        # Remover linhas totalmente vazias
        df = df.dropna(axis=0, how="all")
        # Strip de espaços nos nomes
        df.columns = [str(c).strip() for c in df.columns]
        # Strip de espaços em strings
        for col in df.select_dtypes(include="object"):
            df[col] = df[col].astype(str).str.strip()
        return df.reset_index(drop=True)

    # ── Detecção automática ──────────────────────────────────────────────

    def _detect_group_column(self, df: pd.DataFrame) -> Optional[str]:
        """Heurística: coluna categórica com poucos valores únicos."""
        candidates = []
        for col in df.columns:
            if df[col].dtype == "object" or str(df[col].dtype) == "category":
                nunique = df[col].nunique()
                if 2 <= nunique <= 20:
                    candidates.append((col, nunique))
        if not candidates:
            return None
        # Preferir colunas com nomes sugestivos
        priority_names = ["group", "grupo", "treatment", "tratamento", "condition",
                          "condição", "genotype", "genótipo", "sample", "amostra"]
        for col, _ in candidates:
            if col.lower() in priority_names:
                return col
        # Menos valores únicos = mais provável ser grupo
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def _detect_value_columns(self, df: pd.DataFrame, group_col: Optional[str]) -> list[str]:
        """Seleciona colunas numéricas excluindo a de grupo."""
        exclude = {group_col} if group_col else set()
        cols = []
        for col in df.columns:
            if col in exclude:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                cols.append(col)
        return cols

    def _detect_timepoint_column(self, df: pd.DataFrame, group_col: Optional[str],
                                  value_cols: list[str]) -> Optional[str]:
        """Detecta coluna de tempo/timepoint."""
        time_names = ["time", "tempo", "timepoint", "hora", "dia", "day",
                      "week", "semana", "month", "mês", "min", "minutes"]
        for col in df.columns:
            if col == group_col or col in value_cols:
                continue
            if col.lower() in time_names:
                return col
            if pd.api.types.is_numeric_dtype(df[col]):
                vals = df[col].dropna().sort_values()
                if len(vals) >= 3 and vals.is_monotonic_increasing:
                    return col
        return None

    def _detect_paired(self, df: pd.DataFrame, group_col: Optional[str],
                       n_per_group: dict) -> bool:
        """Detecta se dados são pareados (N igual em todos os grupos)."""
        if not group_col:
            return False
        counts = list(n_per_group.values())
        if len(counts) < 2:
            return False
        # Todos os grupos com mesmo N sugere pareamento
        return len(set(counts)) == 1

    # ── Conversão wide → tidy ────────────────────────────────────────────

    def _wide_to_tidy(self, df: pd.DataFrame) -> tuple:
        """Converte dados wide (cada coluna = grupo) para tidy format."""
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            raise ValueError("Nenhuma coluna numérica encontrada.")

        melted = df[numeric_cols].melt(var_name="group", value_name="value")
        melted = melted.dropna(subset=["value"])
        return melted, "group", ["value"]

    # ── Validação ────────────────────────────────────────────────────────

    def _validate(self, df: pd.DataFrame, group_col: Optional[str],
                  value_cols: list[str]) -> list[str]:
        warnings = []

        # NaN check
        for col in value_cols:
            na_count = df[col].isna().sum()
            if na_count > 0:
                pct = na_count / len(df) * 100
                warnings.append(f"Coluna '{col}': {na_count} valores faltantes ({pct:.1f}%)")

        # N mínimo
        if group_col:
            for grp in df[group_col].unique():
                n = df[df[group_col] == grp].shape[0]
                if n < 3:
                    warnings.append(f"Grupo '{grp}': apenas {n} observações (mínimo recomendado: 3)")

        # Outliers extremos (> 4 SD)
        for col in value_cols:
            vals = df[col].dropna()
            if len(vals) > 5:
                mean, std = vals.mean(), vals.std()
                if std > 0:
                    n_outliers = ((vals - mean).abs() > 4 * std).sum()
                    if n_outliers > 0:
                        warnings.append(f"Coluna '{col}': {n_outliers} outlier(s) extremo(s) (> 4 SD)")

        return warnings
