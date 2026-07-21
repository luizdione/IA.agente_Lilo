"""
Skill: constants_value
Fonte: scipy.constants.value (scipy v1.15.3)
Complexidade: simple
Tags: geral
"""


def constants_value(key: str):
    """
    Value in physical_constants indexed by key

Parameters
----------
key : Python string
    Key in dictionary `physical_constants`

Returns
-------
value : float
    Value in `physical_constants` corresponding to `key`

Examples
--------
>>> from scipy import constants
>>> constants.value('elementary ...

    Args:
        key: str — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.constants.value
    """
    try:
        from scipy.constants import value

        result = value(key)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "constants_value"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "constants_value"}


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
