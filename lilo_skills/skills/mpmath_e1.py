"""
Skill: mpmath_e1
Fonte: mpmath.e1 (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_e1(x: str, kwargs: str):
    """
    Computes the exponential integral `\mathrm{E}_1(z)`, given by

.. math ::

    \mathrm{E}_1(z) = \int_z^{\infty} \frac{e^{-t}}{t} dt.

This is equivalent to :func:`~mpmath.expint` with `n = 1`.

**Examples**

Two ways to evaluate this function::

    >>> from mpmath import *
    >>> mp.dps = 25; mp....

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.e1
    """
    try:
        from mpmath import e1

        result = e1(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_e1"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_e1"}


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
