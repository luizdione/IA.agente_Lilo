"""
Skill: mpmath_cos
Fonte: mpmath.cos (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_cos(x: str, kwargs: str):
    r"""
    Computes the cosine of `x`, `\cos(x)`.

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> cos(pi/3)
    0.5
    >>> cos(100000001)
    -0.9802850113244713353133243
    >>> cos(2+3j)
    (-4.189625690968807230132555 - 9.109227893755336597979197j)
    >>> cos(inf)
    nan
    ...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.cos
    """
    try:
        from mpmath import cos

        result = cos(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_cos"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_cos"}


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
