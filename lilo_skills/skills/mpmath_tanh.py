"""
Skill: mpmath_tanh
Fonte: mpmath.tanh (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_tanh(x: str, kwargs: str):
    r"""
    Computes the hyperbolic tangent of `x`,
`\tanh(x) = \sinh(x)/\cosh(x)`. Values and limits include::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> tanh(0)
    0.0
    >>> tanh(1)
    0.7615941559557648881194583
    >>> tanh(-inf), tanh(inf)
    (-1.0, 1.0)

The hyperboli...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.tanh
    """
    try:
        from mpmath import tanh

        result = tanh(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_tanh"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_tanh"}


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
