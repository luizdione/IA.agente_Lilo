"""
Skill: escape_squeeze
Fonte: tornado.escape.squeeze (tornado v6.1)
Complexidade: simple
Tags: bioinformatica
"""


def escape_squeeze(value: str):
    """
    Replace all sequences of whitespace chars with a single space.

    Args:
        value: str — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.squeeze
    """
    try:
        from tornado.escape import squeeze

        result = squeeze(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_squeeze"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_squeeze"}


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
