"""
Skill: seaborn_crayon_palette
Fonte: seaborn.crayon_palette (seaborn v0.13.2)
Complexidade: simple
Tags: geral
"""


def seaborn_crayon_palette(colors: str):
    """
    Make a palette with color names from Crayola crayons.

Colors are taken from here:
https://en.wikipedia.org/wiki/List_of_Crayola_crayon_colors

This is just a simple wrapper around the `seaborn.crayons` dictionary.

Parameters
----------
colors : list of strings
    List of keys in the `seaborn.cray...

    Args:
        colors: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.crayon_palette
    """
    try:
        from seaborn import crayon_palette

        result = crayon_palette(colors)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_crayon_palette"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_crayon_palette"}


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
