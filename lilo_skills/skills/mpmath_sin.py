"""
Skill: mpmath_sin
Fonte: mpmath.sin (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_sin(x: str, kwargs: str):
    r"""
    Computes the sine of `x`, `\sin(x)`.

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> sin(pi/3)
    0.8660254037844386467637232
    >>> sin(100000001)
    0.1975887055794968911438743
    >>> sin(2+3j)
    (9.1544991469114295734673 - 4.168906959966564350754813j)
    >>> sin...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.sin
    """
    try:
        from mpmath import sin

        result = sin(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_sin"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_sin"}


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
