"""
Skill: artist_cache
Fonte: matplotlib.artist.cache (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def artist_cache(user_function: str):
    """
    Simple lightweight unbounded cache.  Sometimes called "memoize".

    Args:
        user_function: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.artist.cache
    """
    try:
        from matplotlib.artist import cache

        result = cache(user_function)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "artist_cache"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "artist_cache"}


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
