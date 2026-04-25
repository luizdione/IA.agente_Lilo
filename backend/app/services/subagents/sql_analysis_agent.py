"""
SQL Analysis Agent - Análise estatística de dados SQL
Integração do Analise_SQL com o sistema LILO
"""

from typing import Dict, Any, Optional, List
import structlog
import pandas as pd

from app.services.model_manager import ModelManager, ModelRole

logger = structlog.get_logger()


class SQLAnalysisAgent:
    """Agente especializado em análise de dados SQL"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    async def analyze_data(
        self,
        connection_string: str,
        query: str,
        analysis_type: str = "descriptive"
    ) -> Dict[str, Any]:
        """
        Analisa dados de banco SQL

        Args:
            connection_string: String de conexão (formato: mysql://user:pass@host/db)
            query: Query SQL
            analysis_type: Tipo (descriptive, statistical, comparative)

        Returns:
            Análise estruturada
        """
        logger.info("Analisando dados SQL", type=analysis_type)

        # Conectar e executar query
        df = await self._execute_query(connection_string, query)

        if df is None or df.empty:
            return {"error": "Nenhum dado retornado ou erro na query"}

        # Análise descritiva básica
        desc = {
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "summary": df.describe().to_dict() if len(df) > 0 else {}
        }

        # Análise com LLM
        prompt = await self._build_analysis_prompt(df, analysis_type)

        analysis = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.ANALYSIS,
            system_prompt="""Você é um especialista em análise estatística de dados
biológicos e científicos. Forneça análises precisas, estatísticas relevantes e
interpretações biológicas quando aplicável.""",
            temperature=0.2
        )

        return {
            "analysis_type": analysis_type,
            "data_summary": desc,
            "llm_analysis": analysis,
            "sample_data": df.head(10).to_dict('records')
        }

    async def _execute_query(
        self,
        connection_string: str,
        query: str
    ) -> Optional[pd.DataFrame]:
        """Executa query SQL e retorna DataFrame"""
        try:
            import sqlalchemy
            from sqlalchemy import create_engine

            engine = create_engine(connection_string)

            with engine.connect() as conn:
                df = pd.read_sql(query, conn)

            logger.info("Query executada", rows=len(df), cols=len(df.columns))
            return df

        except Exception as e:
            logger.error("Erro ao executar query", error=str(e))
            return None

    async def _build_analysis_prompt(
        self,
        df: pd.DataFrame,
        analysis_type: str
    ) -> str:
        """Constrói prompt para análise"""

        # Estatísticas básicas
        stats = df.describe().to_string()

        # Amostra de dados
        sample = df.head(20).to_string()

        # Tipos de colunas
        dtypes = "\n".join([f"- {col}: {dtype}" for col, dtype in df.dtypes.items()])

        if analysis_type == "descriptive":
            prompt = f"""Analise os seguintes dados e forneça uma análise descritiva completa.

Colunas e tipos:
{dtypes}

Estatísticas descritivas:
{stats}

Amostra dos dados (primeiras linhas):
{sample}

Forneça:
1. Visão geral dos dados
2. Observações sobre distribuições
3. Valores atípicos ou padrões interessantes
4. Sugestões de análises adicionais

Análise:"""

        elif analysis_type == "statistical":
            prompt = f"""Realize uma análise estatística dos dados fornecidos.

Colunas e tipos:
{dtypes}

Estatísticas:
{stats}

Amostra:
{sample}

Forneça:
1. Testes estatísticos apropriados
2. Correlações entre variáveis
3. Significância estatística
4. Interpretação dos resultados

Análise estatística:"""

        elif analysis_type == "comparative":
            # Detectar colunas para comparação
            grouping_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

            prompt = f"""Realize uma análise comparativa dos dados.

Colunas categóricas (para agrupamento):
{', '.join(grouping_cols)}

Estatísticas por grupo:
{stats}

Amostra:
{sample}

Forneça:
1. Comparações entre grupos
2. Diferenças significativas
3. Padrões em cada grupo
4. Conclusões da comparação

Análise comparativa:"""

        else:
            prompt = f"""Analise os dados fornecidos.

Dados:
{sample}

Estatísticas:
{stats}

Análise:"""

        return prompt

    async def generate_sql(
        self,
        table_schema: Dict[str, Any],
        natural_query: str
    ) -> str:
        """
        Gera SQL a partir de linguagem natural

        Args:
            table_schema: Schema da tabela (nome, colunas, tipos)
            natural_query: Query em linguagem natural

        Returns:
            SQL gerado
        """
        schema_str = "\n".join([
            f"- {col}: {dtype}"
            for col, dtype in table_schema.get("columns", {}).items()
        ])

        prompt = f"""Gere uma query SQL válida para a seguinte solicitação.

Tabela: {table_schema.get('table_name', 'unknown')}

Schema:
{schema_str}

Solicitação: {natural_query}

Gere APENAS a query SQL, sem explicações:"""

        sql = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.ANALYSIS,
            temperature=0.1
        )

        # Limpar query
        sql = sql.strip()

        # Remover markdown code blocks se existir
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        logger.info("SQL gerado", query=sql)
        return sql

    async def explain_query(self, query: str) -> str:
        """
        Explica uma query SQL

        Args:
            query: Query SQL

        Returns:
            Explicação em linguagem natural
        """
        prompt = f"""Explique a seguinte query SQL de forma clara e didática.

Query:
{query}

Explicação:"""

        explanation = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.ANALYSIS,
            temperature=0.3
        )

        return explanation
