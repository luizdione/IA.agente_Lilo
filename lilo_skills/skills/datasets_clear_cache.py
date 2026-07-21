"""
Skill: datasets_clear_cache
Fonte: scipy.datasets.clear_cache (scipy v1.15.3)
Complexidade: simple
Tags: geral
"""


def datasets_clear_cache(datasets: str = None):
    """
    Cleans the scipy datasets cache directory.

If a scipy.datasets method or a list/tuple of the same is
provided, then clear_cache removes all the data files
associated to the passed dataset method callable(s).

By default, it removes all the cached data files.

Parameters
----------
datasets : callab...

    Args:
        datasets: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.datasets.clear_cache
    """
    try:
        from scipy.datasets import clear_cache

        result = clear_cache(datasets)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "datasets_clear_cache"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "datasets_clear_cache"}


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
