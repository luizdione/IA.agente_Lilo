# Analise_SQL — Subagente SQL/estatística (LILO)

`SQLAgent` (`agent.py`) é um subagente `BaseAgent` que **gera/explica SQL** e
**sugere análises estatísticas** para dados tabulares biológicos, via LLM local.
Roda dentro do LILO — não é um app GUI standalone.

- **Tools:** `sql_query` (gera/explica SQL a partir de linguagem natural) e
  `sql_stats` (sugere testes estatísticos + queries).
- **Modos auto-detectados** (`run`): `generate`, `explain`, `stats`, chat livre.
- **Padrão:** SQLite (MySQL se especificado), 100% local (Ollama), em português.

Documentação completa: [`docs/agentes/Analise_SQL.md`](../../docs/agentes/Analise_SQL.md).

```python
from agents.Analise_SQL.agent import SQLAgent
print(SQLAgent().run("gere uma query para contar amostras por espécie"))
```

> Histórico: a GUI autônoma anterior (customtkinter, presets de servidor) foi
> arquivada em `_ARCHIVE_v10/`. Não embuta credenciais de banco em código/docs —
> use variáveis de ambiente.
