"""
Skill: numpy_fromiter
Fonte: numpy.fromiter (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados, visualizacao
"""


def numpy_fromiter(args: str):
    """
    fromiter(iter, dtype, count=-1, *, like=None)

Create a new 1-dimensional array from an iterable object.

Parameters
----------
iter : iterable object
    An iterable object providing data for the array.
dtype : data-type
    The data-type of the returned array.

    .. versionchanged:: 1.23
       ...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.fromiter
    """
    try:
        from numpy import fromiter

        result = fromiter(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_fromiter"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_fromiter"}


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
