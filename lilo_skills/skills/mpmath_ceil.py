"""
Skill: mpmath_ceil
Fonte: mpmath.ceil (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_ceil(x: str, kwargs: str):
    r"""
    Computes the ceiling of `x`, `\lceil x \rceil`, defined as
the smallest integer greater than or equal to `x`::

    >>> from mpmath import *
    >>> mp.pretty = False
    >>> ceil(3.5)
    mpf('4.0')

The ceiling function is defined for complex numbers and
acts on the real and imaginary parts separa...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ceil
    """
    try:
        from mpmath import ceil

        result = ceil(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_ceil"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_ceil"}


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
