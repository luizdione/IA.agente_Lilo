"""
Skill: seaborn_saturate
Fonte: seaborn.saturate (seaborn v0.13.2)
Complexidade: simple
Tags: visualizacao
"""


def seaborn_saturate(color: str):
    """
    Return a fully saturated color with the same hue.

Parameters
----------
color : matplotlib color
    hex, rgb-tuple, or html color name

Returns
-------
new_color : rgb tuple
    saturated color code in RGB tuple representation

    Args:
        color: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.saturate
    """
    try:
        from seaborn import saturate

        result = saturate(color)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_saturate"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_saturate"}


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
