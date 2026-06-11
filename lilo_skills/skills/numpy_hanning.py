"""
Skill: numpy_hanning
Fonte: numpy.hanning (numpy v2.2.6)
Complexidade: simple
Tags: matematica, visualizacao
"""


def numpy_hanning(M: str):
    """
    Return the Hanning window.

The Hanning window is a taper formed by using a weighted cosine.

Parameters
----------
M : int
    Number of points in the output window. If zero or less, an
    empty array is returned.

Returns
-------
out : ndarray, shape(M,)
    The window, with the maximum value nor...

    Args:
        M: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.hanning
    """
    try:
        from numpy import hanning

        result = hanning(M)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_hanning"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_hanning"}


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
