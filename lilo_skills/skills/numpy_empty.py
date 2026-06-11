"""
Skill: numpy_empty
Fonte: numpy.empty (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_empty(args: str):
    """
    empty(shape, dtype=float, order='C', *, device=None, like=None)

Return a new array of given shape and type, without initializing entries.

Parameters
----------
shape : int or tuple of int
    Shape of the empty array, e.g., ``(2, 3)`` or ``2``.
dtype : data-type, optional
    Desired output data-t...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.empty
    """
    try:
        from numpy import empty

        result = empty(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_empty"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_empty"}


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
