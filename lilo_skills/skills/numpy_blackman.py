"""
Skill: numpy_blackman
Fonte: numpy.blackman (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_blackman(M: str):
    """
    Return the Blackman window.

The Blackman window is a taper formed by using the first three
terms of a summation of cosines. It was designed to have close to the
minimal leakage possible.  It is close to optimal, only slightly worse
than a Kaiser window.

Parameters
----------
M : int
    Number of ...

    Args:
        M: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.blackman
    """
    try:
        from numpy import blackman

        result = blackman(M)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_blackman"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_blackman"}


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
