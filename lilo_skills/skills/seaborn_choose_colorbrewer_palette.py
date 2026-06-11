"""
Skill: seaborn_choose_colorbrewer_palette
Fonte: seaborn.choose_colorbrewer_palette (seaborn v0.13.2)
Complexidade: simple
Tags: bioinformatica, visualizacao
"""


def seaborn_choose_colorbrewer_palette(data_type: str, as_cmap: str = False):
    """
    Select a palette from the ColorBrewer set.

These palettes are built into matplotlib and can be used by name in
many seaborn functions, or by passing the object returned by this function.

Parameters
----------
data_type : {'sequential', 'diverging', 'qualitative'}
    This describes the kind of dat...

    Args:
        data_type: Any — ver docstring original
        as_cmap: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.choose_colorbrewer_palette
    """
    try:
        from seaborn import choose_colorbrewer_palette

        result = choose_colorbrewer_palette(data_type, as_cmap)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_choose_colorbrewer_palette"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_choose_colorbrewer_palette"}


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
