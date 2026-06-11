"""
Skill: numpy_arange
Fonte: numpy.arange (numpy v2.2.6)
Complexidade: simple
Tags: bioinformatica
"""


def numpy_arange(args: str):
    """
    arange([start,] stop[, step,], dtype=None, *, device=None, like=None)

Return evenly spaced values within a given interval.

``arange`` can be called with a varying number of positional arguments:

* ``arange(stop)``: Values are generated within the half-open interval
  ``[0, stop)`` (in other words...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.arange
    """
    try:
        from numpy import arange

        result = arange(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_arange"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_arange"}


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
