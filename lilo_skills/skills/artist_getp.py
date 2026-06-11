"""
Skill: artist_getp
Fonte: matplotlib.artist.getp (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def artist_getp(obj: str, property: str = None):
    """
    Return the value of an `.Artist`'s *property*, or print all of them.

Parameters
----------
obj : `~matplotlib.artist.Artist`
    The queried artist; e.g., a `.Line2D`, a `.Text`, or an `~.axes.Axes`.

property : str or None, default: None
    If *property* is 'somename', this function returns
    `...

    Args:
        obj: Any — ver docstring original
        property: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.artist.getp
    """
    try:
        from matplotlib.artist import getp

        result = getp(obj, property)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "artist_getp"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "artist_getp"}


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
