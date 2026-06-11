"""
Skill: differentiate_xp_copy
Fonte: scipy.differentiate.xp_copy (scipy v1.15.3)
Complexidade: medium
Tags: geral
"""


def differentiate_xp_copy(x: str, xp: str = None):
    """
    Copies an array.

Parameters
----------
x : array

xp : array_namespace

Returns
-------
copy : array
    Copied array

Notes
-----
This copy function does not offer all the semantics of `np.copy`, i.e. the
`subok` and `order` keywords are not used.

    Args:
        x: Any — ver docstring original
        xp: module | None — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.differentiate.xp_copy
    """
    try:
        from scipy.differentiate import xp_copy

        result = xp_copy(x, xp)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "differentiate_xp_copy"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "differentiate_xp_copy"}


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
