"""
Skill: mpmath_sinh
Fonte: mpmath.sinh (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_sinh(x: str, kwargs: str):
    """
    Computes the hyperbolic sine of `x`,
`\sinh(x) = (e^x - e^{-x})/2`. Values and limits include::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> sinh(0)
    0.0
    >>> sinh(1)
    1.175201193643801456882382
    >>> sinh(-inf), sinh(+inf)
    (-inf, +inf)

The hyperbolic s...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.sinh
    """
    try:
        from mpmath import sinh

        result = sinh(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_sinh"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_sinh"}


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
