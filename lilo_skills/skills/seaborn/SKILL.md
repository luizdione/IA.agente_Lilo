---
name: seaborn
description: Visualizacao estatistica de alto-nivel sobre matplotlib.
triggers: ['seaborn', 'heatmap', 'violinplot', 'pairplot', 'regplot']
functions: 13
source: lilo_skills/registry.json
---

# seaborn


Funcoes expostas via `lilo_skills` (13 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("seaborn_get_dataset_names", **kwargs)
```


## Funcoes

- **seaborn_axes_style** -- `seaborn.axes_style` -- 2 parametro(s) [bioinformatica, visualizacao]
- **seaborn_choose_colorbrewer_palette** -- `seaborn.choose_colorbrewer_palette` -- 2 parametro(s) [bioinformatica, visualizacao]
- **seaborn_choose_cubehelix_palette** -- `seaborn.choose_cubehelix_palette` -- 1 parametro(s) [bioinformatica]
- **seaborn_choose_dark_palette** -- `seaborn.choose_dark_palette` -- 2 parametro(s) [bioinformatica]
- **seaborn_choose_diverging_palette** -- `seaborn.choose_diverging_palette` -- 1 parametro(s) [machine_learning, visualizacao]
- **seaborn_choose_light_palette** -- `seaborn.choose_light_palette` -- 2 parametro(s) [bioinformatica]
- **seaborn_crayon_palette** -- `seaborn.crayon_palette` -- 1 parametro(s) [geral]
- **seaborn_desaturate** -- `seaborn.desaturate` -- 2 parametro(s) [visualizacao]
- **seaborn_get_data_home** -- `seaborn.get_data_home` -- 1 parametro(s) [manipulacao_dados]
- **seaborn_get_dataset_names** -- `seaborn.get_dataset_names` -- 0 parametro(s) [geral]
- **seaborn_reset_defaults** -- `seaborn.reset_defaults` -- 0 parametro(s) [geral]
- **seaborn_reset_orig** -- `seaborn.reset_orig` -- 0 parametro(s) [geral]
- **seaborn_saturate** -- `seaborn.saturate` -- 1 parametro(s) [visualizacao]
