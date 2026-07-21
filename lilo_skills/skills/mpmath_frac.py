"""
Skill: mpmath_frac
Fonte: mpmath.frac (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_frac(x: str, kwargs: str):
    r"""
    Gives the fractional part of `x`, defined as
`\mathrm{frac}(x) = x - \lfloor x \rfloor` (see :func:`~mpmath.floor`).
In effect, this computes `x` modulo 1, or `x+n` where
`n \in \mathbb{Z}` is such that `x+n \in [0,1)`::

    >>> from mpmath import *
    >>> mp.pretty = False
    >>> frac(1.25)
    ...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.frac
    """
    try:
        from mpmath import frac

        result = frac(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_frac"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_frac"}


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
