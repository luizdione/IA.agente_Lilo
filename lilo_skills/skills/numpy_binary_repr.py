"""
Skill: numpy_binary_repr
Fonte: numpy.binary_repr (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_binary_repr(num: str, width: str = None):
    """
    Return the binary representation of the input number as a string.

For negative numbers, if width is not given, a minus sign is added to the
front. If width is given, the two's complement of the number is
returned, with respect to that width.

In a two's-complement system negative numbers are repres...

    Args:
        num: Any — ver docstring original
        width: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.binary_repr
    """
    try:
        from numpy import binary_repr

        result = binary_repr(num, width)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_binary_repr"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_binary_repr"}


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
