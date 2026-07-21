"""
Skill: constants_find
Fonte: scipy.constants.find (scipy v1.15.3)
Complexidade: medium
Tags: geral
"""


def constants_find(sub: str = None, disp: bool = False):
    """
    Return list of physical_constant keys containing a given string.

Parameters
----------
sub : str
    Sub-string to search keys for. By default, return all keys.
disp : bool
    If True, print the keys that are found and return None.
    Otherwise, return the list of keys without printing anything.
...

    Args:
        sub: str | None — ver docstring original
        disp: bool — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.constants.find
    """
    try:
        from scipy.constants import find

        result = find(sub, disp)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "constants_find"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "constants_find"}


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
