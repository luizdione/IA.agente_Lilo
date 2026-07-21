---
name: idna
description: Codificacao IDNA de dominios internacionais.
triggers: ['idna', 'punycode', 'dominio internacional']
functions: 1
source: lilo_skills/registry.json
---

# idna


Funcoes expostas via `lilo_skills` (1 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("intranges_intranges_from_list", **kwargs)
```


## Funcoes

- **intranges_intranges_from_list** -- `idna.intranges.intranges_from_list` -- 1 parametro(s) [bioinformatica]
