"""
Skill: matplotlib_rc
Fonte: matplotlib.rc (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def matplotlib_rc(group: str, kwargs: str):
    """
    Set the current `.rcParams`.  *group* is the grouping for the rc, e.g.,
for ``lines.linewidth`` the group is ``lines``, for
``axes.facecolor``, the group is ``axes``, and so on.  Group may
also be a list or tuple of group names, e.g., (*xtick*, *ytick*).
*kwargs* is a dictionary attribute name/value...

    Args:
        group: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rc
    """
    try:
        from matplotlib import rc

        result = rc(group, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rc"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rc"}


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
