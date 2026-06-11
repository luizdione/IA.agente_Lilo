"""
Skill: numpy_frombuffer
Fonte: numpy.frombuffer (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados
"""


def numpy_frombuffer(args: str):
    """
    frombuffer(buffer, dtype=float, count=-1, offset=0, *, like=None)

Interpret a buffer as a 1-dimensional array.

Parameters
----------
buffer : buffer_like
    An object that exposes the buffer interface.
dtype : data-type, optional
    Data-type of the returned array; default: float.
count : int, o...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.frombuffer
    """
    try:
        from numpy import frombuffer

        result = frombuffer(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_frombuffer"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_frombuffer"}


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
