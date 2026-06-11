"""
Skill: escape_recursive_unicode
Fonte: tornado.escape.recursive_unicode (tornado v6.1)
Complexidade: simple
Tags: manipulacao_dados
"""


def escape_recursive_unicode(obj: str):
    """
    Walks a simple data structure, converting byte strings to unicode.

Supports lists, tuples, and dictionaries.

    Args:
        obj: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.recursive_unicode
    """
    try:
        from tornado.escape import recursive_unicode

        result = recursive_unicode(obj)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_recursive_unicode"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_recursive_unicode"}


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
