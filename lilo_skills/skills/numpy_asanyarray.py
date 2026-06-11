"""
Skill: numpy_asanyarray
Fonte: numpy.asanyarray (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados
"""


def numpy_asanyarray(args: str):
    """
    asanyarray(a, dtype=None, order=None, *, device=None, copy=None, like=None)

Convert the input to an ndarray, but pass ndarray subclasses through.

Parameters
----------
a : array_like
    Input data, in any form that can be converted to an array.  This
    includes scalars, lists, lists of tuples, ...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.asanyarray
    """
    try:
        from numpy import asanyarray

        result = asanyarray(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_asanyarray"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_asanyarray"}


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
