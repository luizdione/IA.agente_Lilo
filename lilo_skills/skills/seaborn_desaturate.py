"""
Skill: seaborn_desaturate
Fonte: seaborn.desaturate (seaborn v0.13.2)
Complexidade: simple
Tags: visualizacao
"""


def seaborn_desaturate(color: str, prop: str):
    """
    Decrease the saturation channel of a color by some percent.

Parameters
----------
color : matplotlib color
    hex, rgb-tuple, or html color name
prop : float
    saturation channel of color will be multiplied by this value

Returns
-------
new_color : rgb tuple
    desaturated color code in RGB tu...

    Args:
        color: Any — ver docstring original
        prop: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.desaturate
    """
    try:
        from seaborn import desaturate

        result = desaturate(color, prop)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_desaturate"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_desaturate"}


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
