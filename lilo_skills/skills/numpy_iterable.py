"""
Skill: numpy_iterable
Fonte: numpy.iterable (numpy v2.2.6)
Complexidade: simple
Tags: bioinformatica
"""


def numpy_iterable(y: str):
    """
    Check whether or not an object can be iterated over.

Parameters
----------
y : object
  Input object.

Returns
-------
b : bool
  Return ``True`` if the object has an iterator method or is a
  sequence and ``False`` otherwise.


Examples
--------
>>> import numpy as np
>>> np.iterable([1, 2, 3])
Tr...

    Args:
        y: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.iterable
    """
    try:
        from numpy import iterable

        result = iterable(y)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_iterable"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_iterable"}


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
