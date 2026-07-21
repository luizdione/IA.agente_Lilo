"""
Skill: numpy_asarray
Fonte: numpy.asarray (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados
"""


def numpy_asarray(args: str):
    """
    asarray(a, dtype=None, order=None, *, device=None, copy=None, like=None)

Convert the input to an array.

Parameters
----------
a : array_like
    Input data, in any form that can be converted to an array.  This
    includes lists, lists of tuples, tuples, tuples of tuples, tuples
    of lists and n...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.asarray
    """
    try:
        from numpy import asarray

        result = asarray(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_asarray"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_asarray"}


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
