"""
Skill: autoreload_watch
Fonte: tornado.autoreload.watch (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def autoreload_watch(filename: str):
    """
    Add a file to the watch list.

All imported modules are watched by default.

    Args:
        filename: str — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.autoreload.watch
    """
    try:
        from tornado.autoreload import watch

        result = watch(filename)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "autoreload_watch"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "autoreload_watch"}


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
