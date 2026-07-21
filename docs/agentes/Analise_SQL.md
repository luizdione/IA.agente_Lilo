# SQLAgent — Análise SQL e estatística (LILO)

Subagente do LILO (`agents/Analise_SQL/agent.py`, classe `SQLAgent`,
`name = "sql"`) que **gera/explica SQL** e **sugere análises estatísticas** para
dados tabulares biológicos, via LLM local. É um agente `BaseAgent` — roda dentro
do LILO (orquestrador ou pipeline Villa Lobos), **não** é um app GUI standalone.

> Nota: a antiga GUI autônoma (`sql_analyzer_gui.py` + `sql_statistical_analyzer.py`,
> em customtkinter, com presets de servidor) foi arquivada em `_ARCHIVE_v10/`.
> Esta página documenta o **agente** atual.

## Tools expostas (`get_tools`)

| Tool | Função |
|------|--------|
| `sql_query` | Gera ou explica queries SQL a partir de linguagem natural. Params: `query` (obrigatório), `db_path`, `table`. |
| `sql_stats` | Sugere análises estatísticas + queries para dados tabulares. Params: `query` (obrigatório), `table`. |

## Comportamento (`run`)

O método detecta o **modo** automaticamente a partir da query (`_detect_mode`):

- `generate` — gera a query SQL (query completa + explicação linha a linha + exemplo de resultado);
- `explain` — explica uma query existente (propósito, cláusulas, performance, melhorias);
- `stats` — sugere testes (normalidade, comparativos), as queries de cada análise e a interpretação;
- *default* — chat livre com contexto SQL.

A geração assume **SQLite** por padrão (MySQL se especificado) e sempre devolve
código executável e comentado, em português.

## Características de roteamento

- `cost_tier = "ollama"` (100% local — SQLite/duckdb), `local_only = True`,
  `latency_class = "fast"`.
- `KEYWORDS` (sql, query, select, tabela, banco, estatística, anova, t-test,
  shapiro, …) alimentam o roteamento do Villa Lobos / `_detect_domain` para o
  domínio `sql`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("sql_query",
                       {"query": "média de expressão por grupo na tabela amostras"}))
```

Ou pela aba **SQL** do dashboard (`dashboard.py`, porta 8100), ou via MCP
(`lilo_sql`).

> Segurança: o agente não embute credenciais de banco. Conexões reais a um SGBD
> devem usar variáveis de ambiente/segredos do seu lado — nunca versionar
> host/usuário/senha em documentação ou código.
