"""
Skill: numpy_asfortranarray
Fonte: numpy.asfortranarray (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_asfortranarray(args: str):
    """
    asfortranarray(a, dtype=None, *, like=None)

Return an array (ndim >= 1) laid out in Fortran order in memory.

Parameters
----------
a : array_like
    Input array.
dtype : str or dtype object, optional
    By default, the data-type is inferred from the input data.
like : array_like, optional
    Re...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.asfortranarray
    """
    try:
        from numpy import asfortranarray

        result = asfortranarray(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_asfortranarray"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_asfortranarray"}


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
