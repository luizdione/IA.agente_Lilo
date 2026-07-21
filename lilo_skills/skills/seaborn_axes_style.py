"""
Skill: seaborn_axes_style
Fonte: seaborn.axes_style (seaborn v0.13.2)
Complexidade: simple
Tags: bioinformatica, visualizacao
"""


def seaborn_axes_style(style: str = None, rc: str = None):
    """
    Get the parameters that control the general style of the plots.

The style parameters control properties like the color of the background and
whether a grid is enabled by default. This is accomplished using the
matplotlib rcParams system.

The options are illustrated in the
:doc:`aesthetics tutorial...

    Args:
        style: Any — ver docstring original
        rc: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.axes_style
    """
    try:
        from seaborn import axes_style

        result = axes_style(style, rc)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_axes_style"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_axes_style"}


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
