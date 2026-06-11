"""
Sistema de Análise Estatística de Dados SQL
============================================
Este módulo implementa um sistema completo em três camadas:
1. Camada de Inspeção de Dados
2. Camada de Decisão Estatística
3. Camada de Execução e Visualização

Funciona como um consultor estatístico automatizado para dados biológicos.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import shapiro, levene, normaltest, mannwhitneyu, kruskal
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
import mysql.connector
from mysql.connector import Error
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
import warnings
warnings.filterwarnings('ignore')


class DatabaseConnection:
    """
    Gerencia conexões com diferentes tipos de bancos de dados.
    Suporta: SQLite local, MySQL local e MySQL remoto.
    """

    def __init__(self):
        self.connection = None
        self.connection_type = None
        self.last_query: Optional[str] = None
        self.last_error: Optional[str] = None

    def quote_identifier(self, identifier: str) -> str:
        """Faz quote seguro de identificadores (tabela/coluna) conforme o tipo de banco."""
        if identifier is None:
            return ""

        ident = str(identifier)

        # Se já vier qualificado com schema (ex.: schema.table), quote por parte.
        if "." in ident:
            parts = [p for p in ident.split(".") if p]
            return ".".join(self.quote_identifier(p) for p in parts)

        if self.connection_type == "mysql":
            return "`" + ident.replace("`", "``") + "`"

        # sqlite (default): aspas duplas
        return '"' + ident.replace('"', '""') + '"'

    def build_select_all_query(self, table_name: str, limit: int = 1000) -> str:
        """Monta um SELECT * seguro para a tabela."""
        t = self.quote_identifier(table_name)
        return f"SELECT * FROM {t} LIMIT {int(limit)}"

    def build_count_query(self, table_name: str) -> str:
        """Monta um SELECT COUNT(*) seguro para a tabela."""
        t = self.quote_identifier(table_name)
        return f"SELECT COUNT(*) AS n FROM {t}"

    def connect_sqlite(self, db_path: str) -> bool:
        """Conecta a um banco SQLite local"""
        try:
            # A UI usa threads para carregar dados. Para SQLite, a conexão precisa
            # permitir acesso entre threads, caso contrário retorna erro silencioso
            # e a UI mostra "Nenhum dado retornado".
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection_type = 'sqlite'
            return True
        except Exception as e:
            print(f"Erro ao conectar SQLite: {e}")
            return False

    def connect_mysql(self, host: str, database: str, user: str, password: str, port: int = 3306) -> bool:
        """Conecta a um banco MySQL (local ou remoto)"""
        try:
            self.connection = mysql.connector.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
            self.connection_type = 'mysql'
            return True
        except Error as e:
            print(f"Erro ao conectar MySQL: {e}")
            return False

    def get_tables(self) -> List[str]:
        """Retorna lista de tabelas disponíveis no banco"""
        if not self.connection:
            return []

        try:
            if self.connection_type == 'sqlite':
                query = "SELECT name FROM sqlite_master WHERE type='table';"
            else:  # mysql
                query = "SHOW TABLES;"

            cursor = self.connection.cursor()
            cursor.execute(query)
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            print(f"Erro ao listar tabelas: {e}")
            return []

    def get_table_columns(self, table_name: str) -> List[str]:
        """Retorna colunas de uma tabela específica"""
        if not self.connection:
            return []

        try:
            if self.connection_type == 'sqlite':
                query = f"PRAGMA table_info({self.quote_identifier(table_name)});"
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns = [col[1] for col in cursor.fetchall()]
            else:  # mysql
                query = f"DESCRIBE {self.quote_identifier(table_name)};"
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns = [col[0] for col in cursor.fetchall()]

            cursor.close()
            return columns
        except Exception as e:
            print(f"Erro ao listar colunas: {e}")
            return []

    def execute_query(self, query: str) -> Optional[pd.DataFrame]:
        """Executa uma query e retorna DataFrame"""
        if not self.connection:
            return None

        try:
            self.last_query = query
            self.last_error = None
            # read_sql_query é mais explícito para SELECT
            df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            self.last_error = str(e)
            print(f"Erro ao executar query: {e}")
            return None

    def execute_scalar(self, query: str) -> Optional[Any]:
        """Executa query e retorna o primeiro valor da primeira linha (útil p/ COUNT)."""
        if not self.connection:
            return None

        try:
            self.last_query = query
            self.last_error = None
            cursor = self.connection.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return None
            return row[0]
        except Exception as e:
            self.last_error = str(e)
            print(f"Erro ao executar scalar: {e}")
            return None

    def close(self):
        """Fecha a conexão com o banco"""
        if self.connection:
            self.connection.close()
            self.connection = None


class BiologicalDataAnalyzer:
    """
    Analisador estatístico automatizado em três camadas.
    Funciona como um consultor estatístico especializado em dados biológicos.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Inicializa o analisador com dados vindos do SQL.

        Args:
            data: DataFrame pandas com os dados a serem analisados
        """
        self.data = data
        self.analysis_report = []
        self.recommendations = []
        self.structure = None
        self.figures = []

    # ==================== CAMADA 1: INSPEÇÃO DE DADOS ====================

    def inspect_data_structure(self) -> Dict:
        """
        Primeira etapa: entender a estrutura dos dados.
        Funciona como um estatístico fazendo perguntas iniciais sobre o experimento.

        Returns:
            Dicionário com informações estruturais dos dados
        """
        inspection = {
            'n_rows': len(self.data),
            'n_columns': len(self.data.columns),
            'column_types': {},
            'missing_data': {},
            'numeric_columns': [],
            'categorical_columns': [],
            'summary_stats': {}
        }

        # Classificar cada coluna e identificar dados faltantes
        for col in self.data.columns:
            inspection['column_types'][col] = str(self.data[col].dtype)
            inspection['missing_data'][col] = self.data[col].isnull().sum()

            if pd.api.types.is_numeric_dtype(self.data[col]):
                inspection['numeric_columns'].append(col)
                # Estatísticas descritivas para colunas numéricas
                inspection['summary_stats'][col] = {
                    'mean': self.data[col].mean(),
                    'median': self.data[col].median(),
                    'std': self.data[col].std(),
                    'min': self.data[col].min(),
                    'max': self.data[col].max(),
                    'q25': self.data[col].quantile(0.25),
                    'q75': self.data[col].quantile(0.75)
                }
            else:
                inspection['categorical_columns'].append(col)
                # Contagem de categorias
                inspection['summary_stats'][col] = {
                    'unique_values': self.data[col].nunique(),
                    'most_common': self.data[col].mode()[0] if len(self.data[col].mode()) > 0 else None,
                    'value_counts': self.data[col].value_counts().to_dict()
                }

        self.structure = inspection
        return inspection

    def check_normality(self, column: str) -> Dict:
        """
        Testa se os dados seguem distribuição normal.
        Crucial porque muitos testes paramétricos assumem normalidade.

        Usa Shapiro-Wilk para amostras pequenas/médias (n < 5000)
        e D'Agostino-Pearson para amostras maiores.

        Args:
            column: Nome da coluna a ser testada

        Returns:
            Dicionário com resultados do teste de normalidade
        """
        data_clean = self.data[column].dropna()
        n = len(data_clean)

        if n < 3:
            return {'test': 'insufficient_data', 'normal': None, 'p_value': None}

        if n < 5000:
            statistic, p_value = shapiro(data_clean)
            test_name = 'Shapiro-Wilk'
        else:
            statistic, p_value = normaltest(data_clean)
            test_name = "D'Agostino-Pearson"

        is_normal = p_value > 0.05

        return {
            'test': test_name,
            'statistic': statistic,
            'p_value': p_value,
            'normal': is_normal,
            'interpretation': f"Dados {'seguem' if is_normal else 'NÃO seguem'} distribuição normal (p={p_value:.4f})"
        }

    def check_variance_homogeneity(self, numeric_col: str, group_col: str) -> Dict:
        """
        Testa se diferentes grupos têm variâncias semelhantes (homogeneidade).
        Importante para decidir entre testes paramétricos regulares ou ajustados.

        Usa teste de Levene, robusto a desvios da normalidade.

        Args:
            numeric_col: Coluna com valores numéricos
            group_col: Coluna com grupos categóricos

        Returns:
            Dicionário com resultados do teste de homogeneidade
        """
        groups = []
        for group_name in self.data[group_col].unique():
            group_data = self.data[self.data[group_col] == group_name][numeric_col].dropna()
            if len(group_data) > 0:
                groups.append(group_data)

        if len(groups) < 2:
            return {'test': 'insufficient_groups', 'homogeneous': None}

        statistic, p_value = levene(*groups)
        is_homogeneous = p_value > 0.05

        return {
            'test': 'Levene',
            'statistic': statistic,
            'p_value': p_value,
            'homogeneous': is_homogeneous,
            'interpretation': f"Variâncias {'são homogêneas' if is_homogeneous else 'NÃO são homogêneas'} (p={p_value:.4f})"
        }

    # ==================== CAMADA 2: DECISÃO ESTATÍSTICA ====================

    def recommend_test(self, numeric_col: str, group_col: Optional[str] = None) -> Dict:
        """
        Função central de decisão estatística.
        Funciona como uma árvore de decisão que um estatístico seguiria.

        Args:
            numeric_col: Coluna com valores numéricos a analisar
            group_col: Coluna com grupos categóricos (opcional)

        Returns:
            Dicionário com recomendação de teste e raciocínio
        """
        recommendation = {
            'variable': numeric_col,
            'test_type': None,
            'test_name': None,
            'reasoning': [],
            'assumptions_checked': {}
        }

        # Verificar normalidade
        normality = self.check_normality(numeric_col)
        recommendation['assumptions_checked']['normality'] = normality
        recommendation['reasoning'].append(normality['interpretation'])

        if group_col is None:
            # Análise univariada
            if normality['normal']:
                recommendation['test_type'] = 'one_sample_t_test'
                recommendation['test_name'] = 'Teste t de uma amostra'
                recommendation['reasoning'].append("Dados normais → teste t paramétrico apropriado")
            else:
                recommendation['test_type'] = 'wilcoxon_signed_rank'
                recommendation['test_name'] = 'Teste de Wilcoxon signed-rank'
                recommendation['reasoning'].append("Dados não-normais → alternativa não-paramétrica")

        else:
            # Análise comparativa entre grupos
            n_groups = self.data[group_col].nunique()
            recommendation['assumptions_checked']['n_groups'] = n_groups

            if n_groups == 2:
                if normality['normal']:
                    variance_check = self.check_variance_homogeneity(numeric_col, group_col)
                    recommendation['assumptions_checked']['variance_homogeneity'] = variance_check
                    recommendation['reasoning'].append(variance_check['interpretation'])

                    if variance_check['homogeneous']:
                        recommendation['test_type'] = 'independent_t_test'
                        recommendation['test_name'] = 'Teste t independente'
                        recommendation['reasoning'].append(
                            "Dados normais + variâncias homogêneas → teste t clássico")
                    else:
                        recommendation['test_type'] = 'welch_t_test'
                        recommendation['test_name'] = "Teste t de Welch"
                        recommendation['reasoning'].append(
                            "Dados normais + variâncias heterogêneas → teste t de Welch (mais robusto)")
                else:
                    recommendation['test_type'] = 'mann_whitney'
                    recommendation['test_name'] = 'Teste de Mann-Whitney U'
                    recommendation['reasoning'].append(
                        "Dados não-normais → teste não-paramétrico Mann-Whitney")

            elif n_groups > 2:
                if normality['normal']:
                    variance_check = self.check_variance_homogeneity(numeric_col, group_col)
                    recommendation['assumptions_checked']['variance_homogeneity'] = variance_check
                    recommendation['reasoning'].append(variance_check['interpretation'])

                    if variance_check['homogeneous']:
                        recommendation['test_type'] = 'one_way_anova'
                        recommendation['test_name'] = 'ANOVA one-way'
                        recommendation['reasoning'].append(
                            "Múltiplos grupos + dados normais + variâncias homogêneas → ANOVA")
                        recommendation['post_hoc'] = 'Tukey HSD'
                        recommendation['reasoning'].append(
                            "Post-hoc: Tukey HSD para comparações pareadas")
                    else:
                        recommendation['test_type'] = 'welch_anova'
                        recommendation['test_name'] = 'ANOVA de Welch'
                        recommendation['reasoning'].append(
                            "Múltiplos grupos + dados normais + variâncias heterogêneas → ANOVA de Welch")
                        recommendation['post_hoc'] = 'Games-Howell'
                else:
                    recommendation['test_type'] = 'kruskal_wallis'
                    recommendation['test_name'] = 'Teste de Kruskal-Wallis'
                    recommendation['reasoning'].append(
                        "Múltiplos grupos + dados não-normais → Kruskal-Wallis (não-paramétrico)")
                    recommendation['post_hoc'] = 'Dunn'
                    recommendation['reasoning'].append(
                        "Post-hoc: teste de Dunn para comparações pareadas")

        return recommendation

    def recommend_visualization(self, numeric_col: str, group_col: Optional[str] = None) -> Dict:
        """
        Sugere visualizações apropriadas baseadas na estrutura dos dados.

        Args:
            numeric_col: Coluna numérica a visualizar
            group_col: Coluna de grupos (opcional)

        Returns:
            Dicionário com recomendações de visualização
        """
        viz_recommendation = {
            'primary_plot': None,
            'secondary_plots': [],
            'reasoning': []
        }

        if group_col is None:
            viz_recommendation['primary_plot'] = 'histogram_with_kde'
            viz_recommendation['reasoning'].append(
                "Histograma + curva de densidade → mostra distribuição dos dados")
            viz_recommendation['secondary_plots'] = ['boxplot', 'qq_plot']
            viz_recommendation['reasoning'].append(
                "Boxplot → outliers e quartis | Q-Q plot → avaliar normalidade")

        else:
            n_groups = self.data[group_col].nunique()

            if n_groups == 2:
                viz_recommendation['primary_plot'] = 'boxplot_with_points'
                viz_recommendation['reasoning'].append(
                    "Boxplot + pontos individuais → distribuição + observações individuais")
                viz_recommendation['secondary_plots'] = ['violin_plot', 'strip_plot']

            elif n_groups <= 6:
                viz_recommendation['primary_plot'] = 'boxplot_or_violin'
                viz_recommendation['reasoning'].append(
                    "Boxplot/Violin plot → comparação visual clara entre grupos")
                viz_recommendation['secondary_plots'] = ['bar_with_error', 'beeswarm']

            else:
                viz_recommendation['primary_plot'] = 'bar_with_error'
                viz_recommendation['reasoning'].append(
                    "Gráfico de barras + erro padrão → mais legível com muitos grupos")
                viz_recommendation['secondary_plots'] = ['heatmap']

        return viz_recommendation

    # ==================== CAMADA 3: EXECUÇÃO E VISUALIZAÇÃO ====================

    def execute_test(self, numeric_col: str, group_col: Optional[str] = None) -> Dict:
        """
        Executa o teste estatístico recomendado.

        Args:
            numeric_col: Coluna numérica
            group_col: Coluna de grupos (opcional)

        Returns:
            Dicionário com resultados do teste
        """
        recommendation = self.recommend_test(numeric_col, group_col)
        test_type = recommendation['test_type']

        result = {
            'test_name': recommendation['test_name'],
            'test_type': test_type,
            'statistic': None,
            'p_value': None,
            'significant': None,
            'interpretation': None,
            'details': {}
        }

        try:
            if test_type == 'independent_t_test':
                groups = self.data[group_col].unique()
                group1 = self.data[self.data[group_col] == groups[0]][numeric_col].dropna()
                group2 = self.data[self.data[group_col] == groups[1]][numeric_col].dropna()
                statistic, p_value = stats.ttest_ind(group1, group2)
                result['statistic'] = statistic
                result['p_value'] = p_value
                result['significant'] = p_value < 0.05
                result['interpretation'] = f"{'Diferença significativa' if result['significant'] else 'Sem diferença significativa'} entre grupos (p={p_value:.4f})"

            elif test_type == 'welch_t_test':
                groups = self.data[group_col].unique()
                group1 = self.data[self.data[group_col] == groups[0]][numeric_col].dropna()
                group2 = self.data[self.data[group_col] == groups[1]][numeric_col].dropna()
                statistic, p_value = stats.ttest_ind(group1, group2, equal_var=False)
                result['statistic'] = statistic
                result['p_value'] = p_value
                result['significant'] = p_value < 0.05
                result['interpretation'] = f"{'Diferença significativa' if result['significant'] else 'Sem diferença significativa'} entre grupos (p={p_value:.4f})"

            elif test_type == 'mann_whitney':
                groups = self.data[group_col].unique()
                group1 = self.data[self.data[group_col] == groups[0]][numeric_col].dropna()
                group2 = self.data[self.data[group_col] == groups[1]][numeric_col].dropna()
                statistic, p_value = mannwhitneyu(group1, group2)
                result['statistic'] = statistic
                result['p_value'] = p_value
                result['significant'] = p_value < 0.05
                result['interpretation'] = f"{'Diferença significativa' if result['significant'] else 'Sem diferença significativa'} entre grupos (p={p_value:.4f})"

            elif test_type == 'one_way_anova':
                groups = []
                for group_name in self.data[group_col].unique():
                    groups.append(self.data[self.data[group_col] == group_name][numeric_col].dropna())
                statistic, p_value = stats.f_oneway(*groups)
                result['statistic'] = statistic
                result['p_value'] = p_value
                result['significant'] = p_value < 0.05
                result['interpretation'] = f"{'Diferença significativa' if result['significant'] else 'Sem diferença significativa'} entre grupos (p={p_value:.4f})"

                # Post-hoc Tukey se significativo
                if result['significant']:
                    tukey = pairwise_tukeyhsd(self.data[numeric_col], self.data[group_col])
                    result['details']['post_hoc'] = str(tukey)

            elif test_type == 'kruskal_wallis':
                groups = []
                for group_name in self.data[group_col].unique():
                    groups.append(self.data[self.data[group_col] == group_name][numeric_col].dropna())
                statistic, p_value = kruskal(*groups)
                result['statistic'] = statistic
                result['p_value'] = p_value
                result['significant'] = p_value < 0.05
                result['interpretation'] = f"{'Diferença significativa' if result['significant'] else 'Sem diferença significativa'} entre grupos (p={p_value:.4f})"

        except Exception as e:
            result['error'] = str(e)
            result['interpretation'] = f"Erro ao executar teste: {e}"

        return result

    def create_visualizations(self, numeric_col: str, group_col: Optional[str] = None) -> List[plt.Figure]:
        """
        Cria visualizações recomendadas.

        Args:
            numeric_col: Coluna numérica
            group_col: Coluna de grupos (opcional)

        Returns:
            Lista de figuras matplotlib
        """
        figures = []

        if group_col is None:
            # Visualização univariada
            fig, axes = plt.subplots(1, 3, figsize=(15, 4))

            # Histograma com KDE
            axes[0].hist(self.data[numeric_col].dropna(), bins=30, alpha=0.7, edgecolor='black')
            axes[0].set_title(f'Histograma - {numeric_col}')
            axes[0].set_xlabel(numeric_col)
            axes[0].set_ylabel('Frequência')

            # Boxplot
            axes[1].boxplot(self.data[numeric_col].dropna())
            axes[1].set_title(f'Boxplot - {numeric_col}')
            axes[1].set_ylabel(numeric_col)

            # Q-Q Plot
            stats.probplot(self.data[numeric_col].dropna(), dist="norm", plot=axes[2])
            axes[2].set_title(f'Q-Q Plot - {numeric_col}')

            plt.tight_layout()
            figures.append(fig)

        else:
            # Visualização comparativa
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

            # Boxplot com pontos
            self.data.boxplot(column=numeric_col, by=group_col, ax=axes[0])
            axes[0].set_title(f'{numeric_col} por {group_col}')
            axes[0].set_xlabel(group_col)
            axes[0].set_ylabel(numeric_col)
            plt.sca(axes[0])
            plt.xticks(rotation=45)

            # Gráfico de barras com erro padrão
            means = self.data.groupby(group_col)[numeric_col].mean()
            sems = self.data.groupby(group_col)[numeric_col].sem()
            axes[1].bar(range(len(means)), means, yerr=sems, capsize=5, alpha=0.7, edgecolor='black')
            axes[1].set_xticks(range(len(means)))
            axes[1].set_xticklabels(means.index, rotation=45)
            axes[1].set_title(f'Médias ± EP - {numeric_col}')
            axes[1].set_xlabel(group_col)
            axes[1].set_ylabel(numeric_col)

            plt.tight_layout()
            figures.append(fig)

        self.figures = figures
        return figures

    def generate_full_report(self, numeric_col: str, group_col: Optional[str] = None) -> str:
        """
        Gera relatório completo da análise.

        Args:
            numeric_col: Coluna numérica
            group_col: Coluna de grupos (opcional)

        Returns:
            String formatada com relatório completo
        """
        report = []
        report.append("=" * 80)
        report.append("RELATÓRIO DE ANÁLISE ESTATÍSTICA")
        report.append("=" * 80)
        report.append("")

        # Inspeção
        report.append("1. INSPEÇÃO DE DADOS")
        report.append("-" * 80)
        if self.structure is None:
            self.inspect_data_structure()
        report.append(f"Total de observações: {self.structure['n_rows']}")
        report.append(f"Colunas numéricas: {', '.join(self.structure['numeric_columns'])}")
        report.append(f"Colunas categóricas: {', '.join(self.structure['categorical_columns'])}")
        report.append("")

        # Recomendação
        report.append("2. RECOMENDAÇÃO ESTATÍSTICA")
        report.append("-" * 80)
        recommendation = self.recommend_test(numeric_col, group_col)
        report.append(f"Teste recomendado: {recommendation['test_name']}")
        report.append("\nRaciocínio:")
        for reason in recommendation['reasoning']:
            report.append(f"  • {reason}")
        report.append("")

        # Execução
        report.append("3. RESULTADOS DO TESTE")
        report.append("-" * 80)
        result = self.execute_test(numeric_col, group_col)
        report.append(f"Teste: {result['test_name']}")
        if result['statistic'] is not None:
            report.append(f"Estatística: {result['statistic']:.4f}")
        if result['p_value'] is not None:
            report.append(f"P-valor: {result['p_value']:.4f}")
        report.append(f"Interpretação: {result['interpretation']}")

        if 'post_hoc' in result['details']:
            report.append("\nAnálise Post-hoc:")
            report.append(result['details']['post_hoc'])
        report.append("")

        # Visualização
        report.append("4. VISUALIZAÇÃO")
        report.append("-" * 80)
        viz_rec = self.recommend_visualization(numeric_col, group_col)
        report.append(f"Gráfico principal: {viz_rec['primary_plot']}")
        report.append(f"Gráficos secundários: {', '.join(viz_rec['secondary_plots'])}")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)
