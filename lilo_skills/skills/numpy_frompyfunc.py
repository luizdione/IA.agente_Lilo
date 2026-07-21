"""
Skill: numpy_frompyfunc
Fonte: numpy.frompyfunc (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_frompyfunc(args: str):
    """
    frompyfunc(func, /, nin, nout, *[, identity])

Takes an arbitrary Python function and returns a NumPy ufunc.

Can be used, for example, to add broadcasting to a built-in Python
function (see Examples section).

Parameters
----------
func : Python function object
    An arbitrary Python function.
nin...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.frompyfunc
    """
    try:
        from numpy import frompyfunc

        result = frompyfunc(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_frompyfunc"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_frompyfunc"}


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
