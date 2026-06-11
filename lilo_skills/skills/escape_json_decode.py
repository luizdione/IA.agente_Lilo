"""
Skill: escape_json_decode
Fonte: tornado.escape.json_decode (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def escape_json_decode(value: str):
    """
    Returns Python objects for the given JSON string.

Supports both `str` and `bytes` inputs.

    Args:
        value: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.json_decode
    """
    try:
        from tornado.escape import json_decode

        result = json_decode(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_json_decode"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_json_decode"}


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
