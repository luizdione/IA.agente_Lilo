---
name: pandas
description: DataFrames, leitura/escrita CSV/Excel/SQL e analise tabular.
triggers: ['pandas', 'dataframe', 'csv', 'tabela', 'groupby', 'merge']
functions: 7
source: lilo_skills/registry.json
---

# pandas


Funcoes expostas via `lilo_skills` (7 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("pandas_isna", **kwargs)
```


## Funcoes

- **pandas_isna** -- `pandas.isna` -- 1 parametro(s) [geral]
- **pandas_isnull** -- `pandas.isnull` -- 1 parametro(s) [geral]
- **pandas_notna** -- `pandas.notna` -- 1 parametro(s) [geral]
- **pandas_notnull** -- `pandas.notnull` -- 1 parametro(s) [geral]
- **pandas_set_eng_float_format** -- `pandas.set_eng_float_format` -- 2 parametro(s) [machine_learning]
- **pandas_show_versions** -- `pandas.show_versions` -- 1 parametro(s) [manipulacao_dados]
- **pandas_test** -- `pandas.test` -- 2 parametro(s) [estatistica]
