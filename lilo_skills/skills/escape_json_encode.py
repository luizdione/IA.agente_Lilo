"""
Skill: escape_json_encode
Fonte: tornado.escape.json_encode (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def escape_json_encode(value: str):
    """
    JSON-encodes the given Python object.

    Args:
        value: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.json_encode
    """
    try:
        from tornado.escape import json_encode

        result = json_encode(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_json_encode"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_json_encode"}


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
