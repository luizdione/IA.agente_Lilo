---
name: mpmath
description: Aritmetica de precisao arbitraria (real e complexa).
triggers: ['mpmath', 'precisao arbitraria', 'high precision']
functions: 35
source: lilo_skills/registry.json
---

# mpmath


Funcoes expostas via `lilo_skills` (35 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("mpmath_runtests", **kwargs)
```


## Funcoes

- **ctx_iv_dps_to_prec** -- `mpmath.ctx_iv.dps_to_prec` -- 1 parametro(s) [geral]
- **ctx_iv_mpi_from_str** -- `mpmath.ctx_iv.mpi_from_str` -- 2 parametro(s) [manipulacao_dados]
- **ctx_iv_prec_to_dps** -- `mpmath.ctx_iv.prec_to_dps` -- 1 parametro(s) [machine_learning]
- **mpmath_acos** -- `mpmath.acos` -- 2 parametro(s) [matematica]
- **mpmath_asin** -- `mpmath.asin` -- 2 parametro(s) [matematica]
- **mpmath_atan** -- `mpmath.atan` -- 2 parametro(s) [matematica]
- **mpmath_bernfrac** -- `mpmath.bernfrac` -- 1 parametro(s) [matematica]
- **mpmath_cbrt** -- `mpmath.cbrt` -- 2 parametro(s) [matematica]
- **mpmath_ceil** -- `mpmath.ceil` -- 2 parametro(s) [matematica]
- **mpmath_cos** -- `mpmath.cos` -- 2 parametro(s) [matematica]
- **mpmath_cosh** -- `mpmath.cosh` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_e1** -- `mpmath.e1` -- 2 parametro(s) [matematica]
- **mpmath_ei** -- `mpmath.ei` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_ellipk** -- `mpmath.ellipk` -- 2 parametro(s) [matematica, visualizacao]
- **mpmath_exp** -- `mpmath.exp` -- 2 parametro(s) [matematica]
- **mpmath_expj** -- `mpmath.expj` -- 2 parametro(s) [matematica]
- **mpmath_expjpi** -- `mpmath.expjpi` -- 2 parametro(s) [matematica]
- **mpmath_fac** -- `mpmath.fac` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_factorial** -- `mpmath.factorial` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_fib** -- `mpmath.fib` -- 2 parametro(s) [matematica]
- **mpmath_fibonacci** -- `mpmath.fibonacci` -- 2 parametro(s) [matematica]
- **mpmath_floor** -- `mpmath.floor` -- 2 parametro(s) [machine_learning, matematica]
- **mpmath_frac** -- `mpmath.frac` -- 2 parametro(s) [matematica]
- **mpmath_gamma** -- `mpmath.gamma` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_harmonic** -- `mpmath.harmonic` -- 2 parametro(s) [matematica]
- **mpmath_ln** -- `mpmath.ln` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_loggamma** -- `mpmath.loggamma` -- 2 parametro(s) [matematica]
- **mpmath_nint** -- `mpmath.nint` -- 2 parametro(s) [matematica]
- **mpmath_rgamma** -- `mpmath.rgamma` -- 2 parametro(s) [matematica]
- **mpmath_runtests** -- `mpmath.runtests` -- 0 parametro(s) [estatistica, matematica]
- **mpmath_sin** -- `mpmath.sin` -- 2 parametro(s) [matematica]
- **mpmath_sinh** -- `mpmath.sinh` -- 2 parametro(s) [bioinformatica, matematica]
- **mpmath_sqrt** -- `mpmath.sqrt` -- 2 parametro(s) [matematica]
- **mpmath_tan** -- `mpmath.tan` -- 2 parametro(s) [matematica]
- **mpmath_tanh** -- `mpmath.tanh` -- 2 parametro(s) [matematica]
