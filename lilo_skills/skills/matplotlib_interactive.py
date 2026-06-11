"""
Skill: matplotlib_interactive
Fonte: matplotlib.interactive (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_interactive(b: str):
    """
    Set whether to redraw after every plotting command (e.g. `.pyplot.xlabel`).

    Args:
        b: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.interactive
    """
    try:
        from matplotlib import interactive

        result = interactive(b)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_interactive"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_interactive"}


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
