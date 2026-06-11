"""
Skill: escape_url_escape
Fonte: tornado.escape.url_escape (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def escape_url_escape(value: str, plus: bool = True):
    """
    Returns a URL-encoded version of the given value.

If ``plus`` is true (the default), spaces will be represented
as "+" instead of "%20".  This is appropriate for query strings
but not for the path component of a URL.  Note that this default
is the reverse of Python's urllib module.

.. versionadded...

    Args:
        value: Union — ver docstring original
        plus: bool — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.url_escape
    """
    try:
        from tornado.escape import url_escape

        result = url_escape(value, plus)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_url_escape"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_url_escape"}


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
