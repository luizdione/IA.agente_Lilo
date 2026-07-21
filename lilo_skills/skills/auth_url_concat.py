"""
Skill: auth_url_concat
Fonte: tornado.auth.url_concat (tornado v6.1)
Complexidade: simple
Tags: manipulacao_dados
"""


def auth_url_concat(url: str, args: str):
    """
    Concatenate url and arguments regardless of whether
url has existing query parameters.

``args`` may be either a dictionary or a list of key-value pairs
(the latter allows for multiple values with the same key.

>>> url_concat("http://example.com/foo", dict(c="d"))
'http://example.com/foo?c=d'
>>> u...

    Args:
        url: str — ver docstring original
        args: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.auth.url_concat
    """
    try:
        from tornado.auth import url_concat

        result = url_concat(url, args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "auth_url_concat"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "auth_url_concat"}


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
