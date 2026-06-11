"""
Skill: matplotlib_get_backend
Fonte: matplotlib.get_backend (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def matplotlib_get_backend(auto_select: str = True):
    """
    Return the name of the current backend.

Parameters
----------
auto_select : bool, default: True
    Whether to trigger backend resolution if no backend has been
    selected so far. If True, this ensures that a valid backend
    is returned. If False, this returns None if no backend has been
    se...

    Args:
        auto_select: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.get_backend
    """
    try:
        from matplotlib import get_backend

        result = get_backend(auto_select)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_get_backend"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_get_backend"}


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
