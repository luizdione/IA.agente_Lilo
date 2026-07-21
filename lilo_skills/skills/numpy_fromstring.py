"""
Skill: numpy_fromstring
Fonte: numpy.fromstring (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados
"""


def numpy_fromstring(args: str):
    """
    fromstring(string, dtype=float, count=-1, *, sep, like=None)

A new 1-D array initialized from text data in a string.

Parameters
----------
string : str
    A string containing the data.
dtype : data-type, optional
    The data type of the array; default: float.  For binary input data,
    the data...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.fromstring
    """
    try:
        from numpy import fromstring

        result = fromstring(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_fromstring"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_fromstring"}


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
