"""
Skill: numpy_asmatrix
Fonte: numpy.asmatrix (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados, matematica
"""


def numpy_asmatrix(data: str, dtype: str = None):
    """
    Interpret the input as a matrix.

Unlike `matrix`, `asmatrix` does not make a copy if the input is already
a matrix or an ndarray.  Equivalent to ``matrix(data, copy=False)``.

Parameters
----------
data : array_like
    Input data.
dtype : data-type
   Data-type of the output matrix.

Returns
-----...

    Args:
        data: Any — ver docstring original
        dtype: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.asmatrix
    """
    try:
        from numpy import asmatrix

        result = asmatrix(data, dtype)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_asmatrix"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_asmatrix"}


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
