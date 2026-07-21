"""
Skill: mpmath_harmonic
Fonte: mpmath.harmonic (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_harmonic(x: str, kwargs: str):
    r"""
    If `n` is an integer, ``harmonic(n)`` gives a floating-point
approximation of the `n`-th harmonic number `H(n)`, defined as

.. math ::

    H(n) = 1 + \frac{1}{2} + \frac{1}{3} + \ldots + \frac{1}{n}

The first few harmonic numbers are::

    >>> from mpmath import *
    >>> mp.dps = 15; mp.pretty ...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.harmonic
    """
    try:
        from mpmath import harmonic

        result = harmonic(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_harmonic"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_harmonic"}


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
