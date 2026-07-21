"""
Skill: mpmath_cbrt
Fonte: mpmath.cbrt (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_cbrt(x: str, kwargs: str):
    """
    ``cbrt(x)`` computes the cube root of `x`, `x^{1/3}`. This
function is faster and more accurate than raising to a floating-point
fraction::

    >>> from mpmath import *
    >>> mp.dps = 15; mp.pretty = False
    >>> 125**(mpf(1)/3)
    mpf('4.9999999999999991')
    >>> cbrt(125)
    mpf('5.0')

Eve...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.cbrt
    """
    try:
        from mpmath import cbrt

        result = cbrt(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_cbrt"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_cbrt"}


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
