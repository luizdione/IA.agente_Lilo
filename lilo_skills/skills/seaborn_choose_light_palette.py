"""
Skill: seaborn_choose_light_palette
Fonte: seaborn.choose_light_palette (seaborn v0.13.2)
Complexidade: simple
Tags: bioinformatica
"""


def seaborn_choose_light_palette(input: str = "husl", as_cmap: str = False):
    """
    Launch an interactive widget to create a light sequential palette.

This corresponds with the :func:`light_palette` function. This kind
of palette is good for data that range between relatively uninteresting
low values and interesting high values.

Requires IPython 2+ and must be used in the noteboo...

    Args:
        input: Any — ver docstring original
        as_cmap: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.choose_light_palette
    """
    try:
        from seaborn import choose_light_palette

        result = choose_light_palette(input, as_cmap)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_choose_light_palette"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_choose_light_palette"}


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
