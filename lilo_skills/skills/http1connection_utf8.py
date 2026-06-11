"""
Skill: http1connection_utf8
Fonte: tornado.http1connection.utf8 (tornado v6.1)
Complexidade: simple
Tags: manipulacao_dados
"""


def http1connection_utf8(value: str):
    """
    Converts a string argument to a byte string.

If the argument is already a byte string or None, it is returned unchanged.
Otherwise it must be a unicode string and is encoded as utf8.

    Args:
        value: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.http1connection.utf8
    """
    try:
        from tornado.http1connection import utf8

        result = utf8(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "http1connection_utf8"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "http1connection_utf8"}


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
