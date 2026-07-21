---
name: tabulate
description: Renderizacao de tabelas em texto/Markdown a partir de listas.
triggers: ['tabulate', 'tabela texto', 'markdown table']
functions: 2
source: lilo_skills/registry.json
---

# tabulate


Funcoes expostas via `lilo_skills` (2 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("tabulate_reduce", **kwargs)
```


## Funcoes

- **tabulate_reduce** -- `tabulate.reduce` -- 1 parametro(s) [bioinformatica]
- **tabulate_simple_separated_format** -- `tabulate.simple_separated_format` -- 1 parametro(s) [geral]
