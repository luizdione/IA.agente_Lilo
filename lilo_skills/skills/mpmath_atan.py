"""
Skill: mpmath_atan
Fonte: mpmath.atan (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_atan(x: str, kwargs: str):
    """
    Computes the inverse tangent or arctangent of `x`, `\tan^{-1}(x)`.
This is a real-valued function for all real `x`, with range
`(-\pi/2, \pi/2)`.

Basic values are::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> atan(-inf)
    -1.570796326794896619231322
    >>> atan(-1...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.atan
    """
    try:
        from mpmath import atan

        result = atan(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_atan"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_atan"}


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
