"""
Skill: mpmath_gamma
Fonte: mpmath.gamma (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_gamma(x: str, kwargs: str):
    r"""
    Computes the gamma function, `\Gamma(x)`. The gamma function is a
shifted version of the ordinary factorial, satisfying
`\Gamma(n) = (n-1)!` for integers `n > 0`. More generally, it
is defined by

.. math ::

    \Gamma(x) = \int_0^{\infty} t^{x-1} e^{-t}\, dt

for any real or complex `x` with `\Re(...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.gamma
    """
    try:
        from mpmath import gamma

        result = gamma(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_gamma"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_gamma"}


def _serialize(obj):
    """Converte resultado para tipo JSON-safe."""
    import json
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        pass

    # Numpy types
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "item"):
        return obj.item()

    # Pandas
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "to_list"):
        return obj.to_list()

    # Fallback
    return str(obj)
