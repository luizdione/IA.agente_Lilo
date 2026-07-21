"""
Skill: numpy_broadcast_shapes
Fonte: numpy.broadcast_shapes (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_broadcast_shapes(args: str):
    """
    Broadcast the input shapes into a single shape.

:ref:`Learn more about broadcasting here <basics.broadcasting>`.

.. versionadded:: 1.20.0

Parameters
----------
*args : tuples of ints, or ints
    The shapes to be broadcast against each other.

Returns
-------
tuple
    Broadcasted shape.

Raises
...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.broadcast_shapes
    """
    try:
        from numpy import broadcast_shapes

        result = broadcast_shapes(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_broadcast_shapes"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_broadcast_shapes"}


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
