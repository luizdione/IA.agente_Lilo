"""
Analise_SQL/agent.py — Adaptador LILO para o subagente de análise SQL.

Envolve sql_statistical_analyzer.py existente com a interface BaseAgent,
expondo run() e get_tools() para o orquestrador lilo.py.
"""

import sys
from pathlib import Path
from typing import Any

# Garante que shared/ é encontrado a partir da raiz do projeto
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.utils import load_env, sanitize_query, truncate

load_env()


class SQLAgent(BaseAgent):
    """
    Subagente de Análise SQL/Estatística.

    Capacidades:
    - Geração de queries SQL via linguagem natural
    - Análise estatística de dados tabulares (SQLite / MySQL)
    - Explicação de queries existentes
    - Sugestão de visualizações para dados numéricos
    """

    name = "sql"
    description = (
        "Análise de dados SQL, geração de queries, estatística descritiva "
        "e comparativa para bancos SQLite e MySQL."
    )

    # Palavras-chave para roteamento automático pelo orquestrador
    KEYWORDS = [
        "sql", "query", "select", "tabela", "banco", "database",
        "sqlite", "mysql", "dados", "estatística", "media", "média",
        "desvio", "correlação", "anova", "t-test", "shapiro",
    ]

    # V9 (2026-05-22): roteamento cost-aware no Villa_Lobos.
    # SQL/estatística roda 100% local (SQLite/duckdb) -> barato e rápido.
    cost_tier = "ollama"
    local_only = True
    latency_class = "fast"

    def __init__(self):
        super().__init__()
        self._llm = None  # lazy

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    # ── Interface BaseAgent ──────────────────────────────────────────────────

    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        """
        Processa query SQL/estatística.

        Modos detectados automaticamente:
        - 'explain'  → explica uma query existente
        - 'generate' → gera SQL a partir de linguagem natural
        - 'stats'    → análise estatística de uma tabela
        - default    → chat livre com contexto SQL
        """
        query = sanitize_query(query)
        self.log.info(f"SQL query recebida: {truncate(query, 80)}")

        mode = self._detect_mode(query)
        db_path = context.get("db_path", "")
        table   = context.get("table", "")

        system = (
            "Você é o LILO SQL, um especialista em bancos de dados e estatística "
            "para dados biológicos (genômica, proteômica, ecologia). "
            "Use SQLite por padrão a menos que MySQL seja especificado. "
            "Sempre forneça código executável e comentado. Responda em português."
        )

        if mode == "generate":
            prompt = (
                f"Gere uma query SQL para responder à seguinte pergunta:\n\n"
                f"PERGUNTA: {query}\n\n"
                f"{'BANCO: ' + db_path if db_path else ''}"
                f"{'TABELA: ' + table if table else ''}\n\n"
                "Forneça: 1) A query completa, 2) Explicação linha a linha, "
                "3) Exemplo de resultado esperado."
            )
        elif mode == "explain":
            prompt = (
                f"Explique em detalhes a seguinte query SQL:\n\n```sql\n{query}\n```\n\n"
                "Inclua: propósito, cláusulas usadas, performance e possíveis melhorias."
            )
        elif mode == "stats":
            prompt = (
                f"Sugira análises estatísticas para os dados descritos:\n\n{query}\n\n"
                "Inclua: testes de normalidade, testes comparativos adequados, "
                "queries SQL para cada análise e interpretação dos resultados."
            )
        else:
            prompt = query

        try:
            return self.llm.chat(prompt, system=system)
        except Exception as e:
            self.log.error(f"Erro ao chamar LLM: {e}")
            return f"[SQLAgent] Erro: {e}"

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "sql_query",
                "description": "Gera ou explica queries SQL a partir de linguagem natural.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query":   {"type": "string", "description": "Pergunta ou query SQL"},
                        "db_path": {"type": "string", "description": "Caminho para o banco SQLite (opcional)"},
                        "table":   {"type": "string", "description": "Nome da tabela de interesse (opcional)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "sql_stats",
                "description": "Sugere análises estatísticas e queries para dados tabulares biológicos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Descrição dos dados e hipótese a testar"},
                        "table": {"type": "string", "description": "Tabela ou dataset (opcional)"},
                    },
                    "required": ["query"],
                },
            },
        ]

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _detect_mode(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["explain", "explique", "o que faz", "o que é"]):
            return "explain"
        if any(k in q for k in ["estatística", "anova", "t-test", "shapiro", "normalidade", "distribuição"]):
            return "stats"
        if any(k in q for k in ["gere", "crie", "escreva", "gerar", "criar", "quero uma query", "como selecionar"]):
            return "generate"
        if "select" in q or "insert" in q or "update" in q or "delete" in q:
            return "explain"
        return "generate"
