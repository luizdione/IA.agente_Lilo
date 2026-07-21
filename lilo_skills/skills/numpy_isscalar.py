"""
Skill: numpy_isscalar
Fonte: numpy.isscalar (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_isscalar(element: str):
    """
    Returns True if the type of `element` is a scalar type.

Parameters
----------
element : any
    Input argument, can be of any type and shape.

Returns
-------
val : bool
    True if `element` is a scalar type, False if it is not.

See Also
--------
ndim : Get the number of dimensions of an array

N...

    Args:
        element: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.isscalar
    """
    try:
        from numpy import isscalar

        result = isscalar(element)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_isscalar"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_isscalar"}


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
