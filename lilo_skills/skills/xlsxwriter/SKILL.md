---
name: xlsxwriter
description: Criacao de planilhas .xlsx com formatacao, formulas e graficos.
triggers: ['xlsxwriter', 'excel', 'planilha', 'xlsx']
functions: 1
source: lilo_skills/registry.json
---

# xlsxwriter


Funcoes expostas via `lilo_skills` (1 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("chart_quote_sheetname", **kwargs)
```


## Funcoes

- **chart_quote_sheetname** -- `xlsxwriter.chart.quote_sheetname` -- 1 parametro(s) [geral]
