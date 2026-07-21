"""
Skill: numpy_kaiser
Fonte: numpy.kaiser (numpy v2.2.6)
Complexidade: simple
Tags: visualizacao
"""


def numpy_kaiser(M: str, beta: str):
    """
    Return the Kaiser window.

The Kaiser window is a taper formed by using a Bessel function.

Parameters
----------
M : int
    Number of points in the output window. If zero or less, an
    empty array is returned.
beta : float
    Shape parameter for window.

Returns
-------
out : array
    The wind...

    Args:
        M: Any — ver docstring original
        beta: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.kaiser
    """
    try:
        from numpy import kaiser

        result = kaiser(M, beta)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_kaiser"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_kaiser"}


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
