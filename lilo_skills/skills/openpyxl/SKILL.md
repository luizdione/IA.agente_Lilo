---
name: openpyxl
description: Leitura/escrita de planilhas Excel .xlsx sem dependencia de MS Office.
triggers: ['excel', 'xlsx', 'planilha', 'openpyxl']
functions: 2
source: lilo_skills/registry.json
---

# openpyxl


Funcoes expostas via `lilo_skills` (2 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("descriptors_from_iso8601", **kwargs)
```


## Funcoes

- **compat_safe_string** -- `openpyxl.compat.safe_string` -- 1 parametro(s) [geral]
- **descriptors_from_iso8601** -- `openpyxl.descriptors.from_ISO8601` -- 1 parametro(s) [manipulacao_dados]
