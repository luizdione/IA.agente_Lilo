"""
Skill: seaborn_get_data_home
Fonte: seaborn.get_data_home (seaborn v0.13.2)
Complexidade: simple
Tags: manipulacao_dados
"""


def seaborn_get_data_home(data_home: str = None):
    """
    Return a path to the cache directory for example datasets.

This directory is used by :func:`load_dataset`.

If the ``data_home`` argument is not provided, it will use a directory
specified by the `SEABORN_DATA` environment variable (if it exists)
or otherwise default to an OS-appropriate user cache...

    Args:
        data_home: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: seaborn.get_data_home
    """
    try:
        from seaborn import get_data_home

        result = get_data_home(data_home)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "seaborn_get_data_home"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "seaborn_get_data_home"}


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
