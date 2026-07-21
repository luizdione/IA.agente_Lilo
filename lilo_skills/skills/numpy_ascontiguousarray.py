"""
Skill: numpy_ascontiguousarray
Fonte: numpy.ascontiguousarray (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_ascontiguousarray(args: str):
    """
    ascontiguousarray(a, dtype=None, *, like=None)

Return a contiguous array (ndim >= 1) in memory (C order).

Parameters
----------
a : array_like
    Input array.
dtype : str or dtype object, optional
    Data-type of returned array.
like : array_like, optional
    Reference object to allow the creat...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.ascontiguousarray
    """
    try:
        from numpy import ascontiguousarray

        result = ascontiguousarray(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_ascontiguousarray"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_ascontiguousarray"}


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
