---
name: jsonschema
description: Validacao de objetos JSON contra esquema JSON Schema.
triggers: ['jsonschema', 'validar json', 'json schema']
functions: 11
source: lilo_skills/registry.json
---

# jsonschema


Funcoes expostas via `lilo_skills` (11 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("cli_namedany", **kwargs)
```


## Funcoes

- **cli_namedany** -- `jsonschema.cli.namedAny` -- 1 parametro(s) [bioinformatica]
- **cli_validator_for** -- `jsonschema.cli.validator_for` -- 2 parametro(s) [estatistica, quimica]
- **compat_lru_cache** -- `jsonschema.compat.lru_cache` -- 2 parametro(s) [estatistica, machine_learning]
- **compat_pathname2url** -- `jsonschema.compat.pathname2url` -- 1 parametro(s) [bioinformatica, quimica]
- **compat_urlunsplit** -- `jsonschema.compat.urlunsplit` -- 1 parametro(s) [estatistica, manipulacao_dados]
- **exceptions_best_match** -- `jsonschema.exceptions.best_match` -- 2 parametro(s) [bioinformatica]
- **exceptions_by_relevance** -- `jsonschema.exceptions.by_relevance` -- 2 parametro(s) [geral]
- **validators_add_metaclass** -- `jsonschema.validators.add_metaclass` -- 1 parametro(s) [geral]
- **validators_lru_cache** -- `jsonschema.validators.lru_cache` -- 2 parametro(s) [estatistica, machine_learning]
- **validators_validates** -- `jsonschema.validators.validates` -- 1 parametro(s) [quimica]
- **validators_validator_for** -- `jsonschema.validators.validator_for` -- 2 parametro(s) [estatistica, quimica]
