"""
Skill: seaborn_choose_cubehelix_palette
Fonte: seaborn.choose_cubehelix_palette (seaborn v0.13.2)
Complexidade: simple
Tags: bioinformatica
"""


def seaborn_choose_cubehelix_palette(as_cmap: str = False):
    """
    Launch an interactive widget to create a sequential cubehelix palette.

This corresponds with the :func:`cubehelix_palette` function. This kind
of palette is good for data that range between relatively uninteresting
low values and interesting high values. The cubehelix system allows the
palette to h...

    Args:
        as_cmap: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.choose_cubehelix_palette
    """
    try:
        from seaborn import choose_cubehelix_palette

        result = choose_cubehelix_palette(as_cmap)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_choose_cubehelix_palette"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_choose_cubehelix_palette"}


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
