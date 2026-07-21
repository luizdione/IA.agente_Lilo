"""
Skill: mpmath_tan
Fonte: mpmath.tan (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_tan(x: str, kwargs: str):
    r"""
    Computes the tangent of `x`, `\tan(x) = \frac{\sin(x)}{\cos(x)}`.
The tangent function is singular at `x = (n+1/2)\pi`, but
``tan(x)`` always returns a finite result since `(n+1/2)\pi`
cannot be represented exactly using floating-point arithmetic.

    >>> from mpmath import *
    >>> mp.dps = 25; m...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.tan
    """
    try:
        from mpmath import tan

        result = tan(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_tan"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_tan"}


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
