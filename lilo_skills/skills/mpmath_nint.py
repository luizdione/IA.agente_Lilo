"""
Skill: mpmath_nint
Fonte: mpmath.nint (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_nint(x: str, kwargs: str):
    """
    Evaluates the nearest integer function, `\mathrm{nint}(x)`.
This gives the nearest integer to `x`; on a tie, it
gives the nearest even integer::

    >>> from mpmath import *
    >>> mp.pretty = False
    >>> nint(3.2)
    mpf('3.0')
    >>> nint(3.8)
    mpf('4.0')
    >>> nint(3.5)
    mpf('4.0')
...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.nint
    """
    try:
        from mpmath import nint

        result = nint(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_nint"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_nint"}


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
