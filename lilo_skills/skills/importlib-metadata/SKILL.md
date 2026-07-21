---
name: importlib-metadata
description: Introspeccao de metadados de pacotes instalados.
triggers: ['importlib', 'metadata', 'package', 'dist-info']
functions: 11
source: lilo_skills/registry.json
---

# importlib-metadata


Funcoes expostas via `lilo_skills` (11 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("importlib_metadata_packages_distributions", **kwargs)
```


## Funcoes

- **importlib_metadata_distribution** -- `importlib_metadata.distribution` -- 1 parametro(s) [geral]
- **importlib_metadata_distributions** -- `importlib_metadata.distributions` -- 1 parametro(s) [geral]
- **importlib_metadata_entry_points** -- `importlib_metadata.entry_points` -- 1 parametro(s) [estatistica, manipulacao_dados]
- **importlib_metadata_files** -- `importlib_metadata.files` -- 1 parametro(s) [geral]
- **importlib_metadata_install** -- `importlib_metadata.install` -- 0 parametro(s) [geral]
- **importlib_metadata_metadata** -- `importlib_metadata.metadata` -- 1 parametro(s) [manipulacao_dados]
- **importlib_metadata_method_cache** -- `importlib_metadata.method_cache` -- 2 parametro(s) [bioinformatica, machine_learning, manipulacao_dados]
- **importlib_metadata_packages_distributions** -- `importlib_metadata.packages_distributions` -- 0 parametro(s) [bioinformatica]
- **importlib_metadata_pypy_partial** -- `importlib_metadata.pypy_partial` -- 1 parametro(s) [geral]
- **importlib_metadata_requires** -- `importlib_metadata.requires` -- 1 parametro(s) [geral]
- **importlib_metadata_version** -- `importlib_metadata.version` -- 1 parametro(s) [geral]
