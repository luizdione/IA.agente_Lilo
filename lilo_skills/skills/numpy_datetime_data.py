"""
Skill: numpy_datetime_data
Fonte: numpy.datetime_data (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_datetime_data(args: str):
    """
    datetime_data(dtype, /)

Get information about the step size of a date or time type.

The returned tuple can be passed as the second argument of `numpy.datetime64` and
`numpy.timedelta64`.

Parameters
----------
dtype : dtype
    The dtype object, which must be a `datetime64` or `timedelta64` type.
...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.datetime_data
    """
    try:
        from numpy import datetime_data

        result = datetime_data(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_datetime_data"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_datetime_data"}


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
