"""
Skill: compat_urlunsplit
Fonte: jsonschema.compat.urlunsplit (jsonschema v3.2.0)
Complexidade: simple
Tags: estatistica, manipulacao_dados
"""


def compat_urlunsplit(components: str):
    """
    Combine the elements of a tuple as returned by urlsplit() into a
complete URL as a string. The data argument can be any five-item iterable.
This may result in a slightly different, but equivalent URL, if the URL that
was parsed originally had unnecessary delimiters (for example, a ? with an
empty qu...

    Args:
        components: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.compat.urlunsplit
    """
    try:
        from jsonschema.compat import urlunsplit

        result = urlunsplit(components)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "compat_urlunsplit"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "compat_urlunsplit"}


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
