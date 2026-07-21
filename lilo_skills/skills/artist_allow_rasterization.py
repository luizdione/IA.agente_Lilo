"""
Skill: artist_allow_rasterization
Fonte: matplotlib.artist.allow_rasterization (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def artist_allow_rasterization(draw: str):
    """
    Decorator for Artist.draw method. Provides routines
that run before and after the draw call. The before and after functions
are useful for changing artist-dependent renderer attributes or making
other setup function calls, such as starting and flushing a mixed-mode
renderer.

    Args:
        draw: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.artist.allow_rasterization
    """
    try:
        from matplotlib.artist import allow_rasterization

        result = allow_rasterization(draw)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "artist_allow_rasterization"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "artist_allow_rasterization"}


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
