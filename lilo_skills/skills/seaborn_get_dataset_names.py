"""
Skill: seaborn_get_dataset_names
Fonte: seaborn.get_dataset_names (seaborn v0.13.2)
Complexidade: simple
Tags: geral
"""


def seaborn_get_dataset_names():
    """
    Report available example datasets, useful for reporting issues.

Requires an internet connection.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.get_dataset_names
    """
    try:
        from seaborn import get_dataset_names

        result = get_dataset_names()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_get_dataset_names"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_get_dataset_names"}


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
