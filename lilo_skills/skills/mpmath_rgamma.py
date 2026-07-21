"""
Skill: mpmath_rgamma
Fonte: mpmath.rgamma (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_rgamma(x: str, kwargs: str):
    r"""
    Computes the reciprocal of the gamma function, `1/\Gamma(z)`. This
function evaluates to zero at the poles
of the gamma function, `z = 0, -1, -2, \ldots`.

**Examples**

Basic examples::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> rgamma(1)
    1.0
    >>> rgamma(4)
 ...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.rgamma
    """
    try:
        from mpmath import rgamma

        result = rgamma(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_rgamma"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_rgamma"}


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
