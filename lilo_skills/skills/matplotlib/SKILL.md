---
name: matplotlib
description: Visualizacao 2D: plot, hist, scatter, barras, layouts e configuracao do backend.
triggers: ['plot', 'grafico', 'chart', 'matplotlib', 'figura', 'subplot']
functions: 30
source: lilo_skills/registry.json
---

# matplotlib


Funcoes expostas via `lilo_skills` (30 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("matplotlib_get_configdir", **kwargs)
```


## Funcoes

- **artist_allow_rasterization** -- `matplotlib.artist.allow_rasterization` -- 1 parametro(s) [visualizacao]
- **artist_cache** -- `matplotlib.artist.cache` -- 1 parametro(s) [geral]
- **artist_get** -- `matplotlib.artist.get` -- 2 parametro(s) [visualizacao]
- **artist_getp** -- `matplotlib.artist.getp` -- 2 parametro(s) [visualizacao]
- **artist_kwdoc** -- `matplotlib.artist.kwdoc` -- 1 parametro(s) [visualizacao]
- **backend_bases_contextmanager** -- `matplotlib.backend_bases.contextmanager` -- 1 parametro(s) [bioinformatica]
- **backend_bases_get_registered_canvas_class** -- `matplotlib.backend_bases.get_registered_canvas_class` -- 1 parametro(s) [geral]
- **backend_bases_is_interactive** -- `matplotlib.backend_bases.is_interactive` -- 0 parametro(s) [visualizacao]
- **backend_tools_add_tools_to_container** -- `matplotlib.backend_tools.add_tools_to_container` -- 2 parametro(s) [geral]
- **backend_tools_add_tools_to_manager** -- `matplotlib.backend_tools.add_tools_to_manager` -- 2 parametro(s) [geral]
- **bezier_lru_cache** -- `matplotlib.bezier.lru_cache` -- 2 parametro(s) [estatistica, machine_learning]
- **matplotlib_cycler** -- `matplotlib.cycler` -- 2 parametro(s) [geral]
- **matplotlib_get_backend** -- `matplotlib.get_backend` -- 1 parametro(s) [geral]
- **matplotlib_get_cachedir** -- `matplotlib.get_cachedir` -- 0 parametro(s) [geral]
- **matplotlib_get_configdir** -- `matplotlib.get_configdir` -- 0 parametro(s) [visualizacao]
- **matplotlib_get_data_path** -- `matplotlib.get_data_path` -- 0 parametro(s) [visualizacao]
- **matplotlib_interactive** -- `matplotlib.interactive` -- 1 parametro(s) [visualizacao]
- **matplotlib_is_interactive** -- `matplotlib.is_interactive` -- 0 parametro(s) [visualizacao]
- **matplotlib_matplotlib_fname** -- `matplotlib.matplotlib_fname` -- 0 parametro(s) [visualizacao]
- **matplotlib_parse_version** -- `matplotlib.parse_version` -- 1 parametro(s) [manipulacao_dados]
- **matplotlib_rc** -- `matplotlib.rc` -- 2 parametro(s) [geral]
- **matplotlib_rc_context** -- `matplotlib.rc_context` -- 2 parametro(s) [visualizacao]
- **matplotlib_rc_file** -- `matplotlib.rc_file` -- 2 parametro(s) [visualizacao]
- **matplotlib_rc_file_defaults** -- `matplotlib.rc_file_defaults` -- 0 parametro(s) [manipulacao_dados, visualizacao]
- **matplotlib_rc_params** -- `matplotlib.rc_params` -- 1 parametro(s) [visualizacao]
- **matplotlib_rcdefaults** -- `matplotlib.rcdefaults` -- 0 parametro(s) [bioinformatica, manipulacao_dados, visualizacao]
- **matplotlib_sanitize_sequence** -- `matplotlib.sanitize_sequence` -- 1 parametro(s) [bioinformatica, visualizacao]
- **matplotlib_set_loglevel** -- `matplotlib.set_loglevel` -- 1 parametro(s) [visualizacao]
- **matplotlib_use** -- `matplotlib.use` -- 2 parametro(s) [manipulacao_dados, visualizacao]
- **matplotlib_validate_backend** -- `matplotlib.validate_backend` -- 1 parametro(s) [visualizacao]
