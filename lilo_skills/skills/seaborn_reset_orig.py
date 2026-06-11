"""
Skill: seaborn_reset_orig
Fonte: seaborn.reset_orig (seaborn v0.13.2)
Complexidade: simple
Tags: geral
"""


def seaborn_reset_orig():
    """
    Restore all RC params to original settings (respects custom rc).

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.reset_orig
    """
    try:
        from seaborn import reset_orig

        result = reset_orig()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_reset_orig"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_reset_orig"}


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
