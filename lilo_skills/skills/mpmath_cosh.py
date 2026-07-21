"""
Skill: mpmath_cosh
Fonte: mpmath.cosh (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_cosh(x: str, kwargs: str):
    r"""
    Computes the hyperbolic cosine of `x`,
`\cosh(x) = (e^x + e^{-x})/2`. Values and limits include::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> cosh(0)
    1.0
    >>> cosh(1)
    1.543080634815243778477906
    >>> cosh(-inf), cosh(+inf)
    (+inf, +inf)

The hyperbolic...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.cosh
    """
    try:
        from mpmath import cosh

        result = cosh(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_cosh"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_cosh"}


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
