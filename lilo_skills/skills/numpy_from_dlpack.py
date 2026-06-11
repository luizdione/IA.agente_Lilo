"""
Skill: numpy_from_dlpack
Fonte: numpy.from_dlpack (numpy v2.2.6)
Complexidade: simple
Tags: bioinformatica
"""


def numpy_from_dlpack(args: str):
    """
    from_dlpack(x, /, *, device=None, copy=None)

Create a NumPy array from an object implementing the ``__dlpack__``
protocol. Generally, the returned NumPy array is a view of the input
object. See [1]_ and [2]_ for more details.

Parameters
----------
x : object
    A Python object that implements the...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.from_dlpack
    """
    try:
        from numpy import from_dlpack

        result = from_dlpack(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_from_dlpack"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_from_dlpack"}


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
