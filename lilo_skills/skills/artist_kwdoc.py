"""
Skill: artist_kwdoc
Fonte: matplotlib.artist.kwdoc (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def artist_kwdoc(artist: str):
    r"""
    Inspect an `~matplotlib.artist.Artist` class (using `.ArtistInspector`) and
return information about its settable properties and their current values.

Parameters
----------
artist : `~matplotlib.artist.Artist` or an iterable of `Artist`\s

Returns
-------
str
    The settable properties of *artist*...

    Args:
        artist: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.artist.kwdoc
    """
    try:
        from matplotlib.artist import kwdoc

        result = kwdoc(artist)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "artist_kwdoc"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "artist_kwdoc"}


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
