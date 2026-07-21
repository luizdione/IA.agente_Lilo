"""
Skill: matplotlib_get_cachedir
Fonte: matplotlib.get_cachedir (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def matplotlib_get_cachedir():
    """
    Return the string path of the cache directory.

The procedure used to find the directory is the same as for
`get_configdir`, except using ``$XDG_CACHE_HOME``/``$HOME/.cache`` instead.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.get_cachedir
    """
    try:
        from matplotlib import get_cachedir

        result = get_cachedir()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_get_cachedir"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_get_cachedir"}


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
