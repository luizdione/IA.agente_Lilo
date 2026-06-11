"""
Skill: numpy_getbufsize
Fonte: numpy.getbufsize (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_getbufsize():
    """
    Return the size of the buffer used in ufuncs.

Returns
-------
getbufsize : int
    Size of ufunc buffer in bytes.

Examples
--------
>>> import numpy as np
>>> np.getbufsize()
8192

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.getbufsize
    """
    try:
        from numpy import getbufsize

        result = getbufsize()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_getbufsize"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_getbufsize"}


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
