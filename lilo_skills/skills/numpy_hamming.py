"""
Skill: numpy_hamming
Fonte: numpy.hamming (numpy v2.2.6)
Complexidade: simple
Tags: matematica, visualizacao
"""


def numpy_hamming(M: str):
    """
    Return the Hamming window.

The Hamming window is a taper formed by using a weighted cosine.

Parameters
----------
M : int
    Number of points in the output window. If zero or less, an
    empty array is returned.

Returns
-------
out : ndarray
    The window, with the maximum value normalized to ...

    Args:
        M: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.hamming
    """
    try:
        from numpy import hamming

        result = hamming(M)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_hamming"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_hamming"}


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
