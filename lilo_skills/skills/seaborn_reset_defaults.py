"""
Skill: seaborn_reset_defaults
Fonte: seaborn.reset_defaults (seaborn v0.13.2)
Complexidade: simple
Tags: geral
"""


def seaborn_reset_defaults():
    """
    Restore all RC params to default settings.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.reset_defaults
    """
    try:
        from seaborn import reset_defaults

        result = reset_defaults()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_reset_defaults"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_reset_defaults"}


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
