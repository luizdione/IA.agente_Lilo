"""
Skill: autoreload_start
Fonte: tornado.autoreload.start (tornado v6.1)
Complexidade: simple
Tags: estatistica
"""


def autoreload_start(check_time: int = 500):
    """
    Begins watching source files for changes.

.. versionchanged:: 5.0
   The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    Args:
        check_time: int — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.autoreload.start
    """
    try:
        from tornado.autoreload import start

        result = start(check_time)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "autoreload_start"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "autoreload_start"}


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
