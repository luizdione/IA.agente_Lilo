"""
Skill: mpmath_expjpi
Fonte: mpmath.expjpi (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_expjpi(x: str, kwargs: str):
    r"""
    Convenience function for computing `e^{i \pi x}`.
Evaluation is accurate near zeros (see also :func:`~mpmath.cospi`,
:func:`~mpmath.sinpi`)::

    >>> from mpmath import *
    >>> mp.dps = 25; mp.pretty = True
    >>> expjpi(0)
    (1.0 + 0.0j)
    >>> expjpi(1)
    (-1.0 + 0.0j)
    >>> expjpi(0.5)...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.expjpi
    """
    try:
        from mpmath import expjpi

        result = expjpi(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_expjpi"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_expjpi"}


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
