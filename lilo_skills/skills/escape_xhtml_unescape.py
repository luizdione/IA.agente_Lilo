"""
Skill: escape_xhtml_unescape
Fonte: tornado.escape.xhtml_unescape (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def escape_xhtml_unescape(value: str):
    """
    Un-escapes an XML-escaped string.

    Args:
        value: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.xhtml_unescape
    """
    try:
        from tornado.escape import xhtml_unescape

        result = xhtml_unescape(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_xhtml_unescape"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_xhtml_unescape"}


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
