"""
Skill: mpmath_floor
Fonte: mpmath.floor (mpmath v1.3.0)
Complexidade: simple
Tags: machine_learning, matematica
"""


def mpmath_floor(x: str, kwargs: str):
    """
    Computes the floor of `x`, `\lfloor x \rfloor`, defined as
the largest integer less than or equal to `x`::

    >>> from mpmath import *
    >>> mp.pretty = False
    >>> floor(3.5)
    mpf('3.0')

.. note ::

    :func:`~mpmath.floor`, :func:`~mpmath.ceil` and :func:`~mpmath.nint` return a
    floa...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.floor
    """
    try:
        from mpmath import floor

        result = floor(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_floor"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_floor"}


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
