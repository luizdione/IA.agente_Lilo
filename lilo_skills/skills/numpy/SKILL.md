---
name: numpy
description: Array numerico N-D, algebra linear, FFT, RNG e operacoes vetorizadas.
triggers: ['array', 'numpy', 'matriz', 'vetor', 'fft', 'linalg']
functions: 33
source: lilo_skills/registry.json
---

# numpy


Funcoes expostas via `lilo_skills` (33 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("numpy_get_include", **kwargs)
```


## Funcoes

- **numpy_arange** -- `numpy.arange` -- 1 parametro(s) [bioinformatica]
- **numpy_array** -- `numpy.array` -- 1 parametro(s) [bioinformatica]
- **numpy_asanyarray** -- `numpy.asanyarray` -- 1 parametro(s) [manipulacao_dados]
- **numpy_asarray** -- `numpy.asarray` -- 1 parametro(s) [manipulacao_dados]
- **numpy_ascontiguousarray** -- `numpy.ascontiguousarray` -- 1 parametro(s) [geral]
- **numpy_asfortranarray** -- `numpy.asfortranarray` -- 1 parametro(s) [geral]
- **numpy_asmatrix** -- `numpy.asmatrix` -- 2 parametro(s) [manipulacao_dados, matematica]
- **numpy_bartlett** -- `numpy.bartlett` -- 1 parametro(s) [bioinformatica, visualizacao]
- **numpy_binary_repr** -- `numpy.binary_repr` -- 2 parametro(s) [geral]
- **numpy_blackman** -- `numpy.blackman` -- 1 parametro(s) [geral]
- **numpy_broadcast_shapes** -- `numpy.broadcast_shapes` -- 1 parametro(s) [geral]
- **numpy_datetime_data** -- `numpy.datetime_data` -- 1 parametro(s) [geral]
- **numpy_diag_indices** -- `numpy.diag_indices` -- 2 parametro(s) [geral]
- **numpy_empty** -- `numpy.empty` -- 1 parametro(s) [geral]
- **numpy_from_dlpack** -- `numpy.from_dlpack` -- 1 parametro(s) [bioinformatica]
- **numpy_frombuffer** -- `numpy.frombuffer` -- 1 parametro(s) [manipulacao_dados]
- **numpy_fromfile** -- `numpy.fromfile` -- 1 parametro(s) [manipulacao_dados]
- **numpy_fromiter** -- `numpy.fromiter` -- 1 parametro(s) [manipulacao_dados, visualizacao]
- **numpy_frompyfunc** -- `numpy.frompyfunc` -- 1 parametro(s) [geral]
- **numpy_fromstring** -- `numpy.fromstring` -- 1 parametro(s) [manipulacao_dados]
- **numpy_get_include** -- `numpy.get_include` -- 0 parametro(s) [geral]
- **numpy_get_printoptions** -- `numpy.get_printoptions` -- 0 parametro(s) [machine_learning]
- **numpy_getbufsize** -- `numpy.getbufsize` -- 0 parametro(s) [geral]
- **numpy_geterr** -- `numpy.geterr` -- 0 parametro(s) [geral]
- **numpy_geterrcall** -- `numpy.geterrcall` -- 0 parametro(s) [geral]
- **numpy_hamming** -- `numpy.hamming` -- 1 parametro(s) [matematica, visualizacao]
- **numpy_hanning** -- `numpy.hanning` -- 1 parametro(s) [matematica, visualizacao]
- **numpy_isdtype** -- `numpy.isdtype` -- 2 parametro(s) [geral]
- **numpy_isfortran** -- `numpy.isfortran` -- 1 parametro(s) [estatistica]
- **numpy_isscalar** -- `numpy.isscalar` -- 1 parametro(s) [geral]
- **numpy_issubdtype** -- `numpy.issubdtype` -- 2 parametro(s) [geral]
- **numpy_iterable** -- `numpy.iterable` -- 1 parametro(s) [bioinformatica]
- **numpy_kaiser** -- `numpy.kaiser` -- 2 parametro(s) [visualizacao]
