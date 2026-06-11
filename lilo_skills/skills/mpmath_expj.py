"""
Skill: mpmath_expj
Fonte: mpmath.expj (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_expj(x: str, kwargs: str):
    """
    Convenience function for computing `e^{ix}`::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> expj(0)
    (1.0 + 0.0j)
    >>> expj(-1)
    (0.5403023058681397174009366 - 0.8414709848078965066525023j)
    >>> expj(j)
    (0.3678794411714423215955238 + 0.0j)
    >>> expj(1...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.expj
    """
    try:
        from mpmath import expj

        result = expj(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_expj"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_expj"}


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
