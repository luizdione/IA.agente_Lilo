"""
Skill: numpy_bartlett
Fonte: numpy.bartlett (numpy v2.2.6)
Complexidade: simple
Tags: bioinformatica, visualizacao
"""


def numpy_bartlett(M: str):
    """
    Return the Bartlett window.

The Bartlett window is very similar to a triangular window, except
that the end points are at zero.  It is often used in signal
processing for tapering a signal, without generating too much
ripple in the frequency domain.

Parameters
----------
M : int
    Number of poin...

    Args:
        M: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.bartlett
    """
    try:
        from numpy import bartlett

        result = bartlett(M)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_bartlett"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_bartlett"}


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
