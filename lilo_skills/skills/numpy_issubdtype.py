"""
Skill: numpy_issubdtype
Fonte: numpy.issubdtype (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_issubdtype(arg1: str, arg2: str):
    r"""
    Returns True if first argument is a typecode lower/equal in type hierarchy.

This is like the builtin :func:`issubclass`, but for `dtype`\ s.

Parameters
----------
arg1, arg2 : dtype_like
    `dtype` or object coercible to one

Returns
-------
out : bool

See Also
--------
:ref:`arrays.scalars` : O...

    Args:
        arg1: Any — ver docstring original
        arg2: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.issubdtype
    """
    try:
        from numpy import issubdtype

        result = issubdtype(arg1, arg2)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_issubdtype"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_issubdtype"}


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
