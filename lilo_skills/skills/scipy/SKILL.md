---
name: scipy
description: Estatistica, otimizacao, interpolacao, ODEs e processamento de sinal.
triggers: ['scipy', 'estatistica', 'otimizacao', 'interpolar', 'anova', 't-test']
functions: 19
source: lilo_skills/registry.json
---

# scipy


Funcoes expostas via `lilo_skills` (19 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("datasets_ascent", **kwargs)
```


## Funcoes

- **constants_find** -- `scipy.constants.find` -- 2 parametro(s) [geral]
- **constants_precision** -- `scipy.constants.precision` -- 1 parametro(s) [machine_learning]
- **constants_unit** -- `scipy.constants.unit` -- 1 parametro(s) [geral]
- **constants_value** -- `scipy.constants.value` -- 1 parametro(s) [geral]
- **datasets_ascent** -- `scipy.datasets.ascent` -- 0 parametro(s) [estatistica, visualizacao]
- **datasets_clear_cache** -- `scipy.datasets.clear_cache` -- 1 parametro(s) [geral]
- **datasets_download_all** -- `scipy.datasets.download_all` -- 1 parametro(s) [manipulacao_dados]
- **datasets_electrocardiogram** -- `scipy.datasets.electrocardiogram` -- 0 parametro(s) [manipulacao_dados]
- **datasets_face** -- `scipy.datasets.face` -- 1 parametro(s) [visualizacao]
- **differentiate_array_namespace** -- `scipy.differentiate.array_namespace` -- 1 parametro(s) [bioinformatica]
- **differentiate_xp_copy** -- `scipy.differentiate.xp_copy` -- 2 parametro(s) [geral]
- **fft_fftshift** -- `scipy.fft.fftshift` -- 2 parametro(s) [matematica]
- **fft_get_workers** -- `scipy.fft.get_workers` -- 0 parametro(s) [matematica]
- **fft_ifftshift** -- `scipy.fft.ifftshift` -- 2 parametro(s) [matematica]
- **fft_register_backend** -- `scipy.fft.register_backend` -- 1 parametro(s) [matematica]
- **fft_set_workers** -- `scipy.fft.set_workers` -- 1 parametro(s) [matematica]
- **fft_skip_backend** -- `scipy.fft.skip_backend` -- 1 parametro(s) [estatistica, matematica]
- **fftpack_hilbert** -- `scipy.fftpack.hilbert` -- 2 parametro(s) [bioinformatica, manipulacao_dados, matematica]
- **scipy_show_config** -- `scipy.show_config` -- 1 parametro(s) [manipulacao_dados]
