"""
Skill: gen_is_coroutine_function
Fonte: tornado.gen.is_coroutine_function (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def gen_is_coroutine_function(func: str):
    """
    Return whether *func* is a coroutine function, i.e. a function
wrapped with `~.gen.coroutine`.

.. versionadded:: 4.5

    Args:
        func: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.is_coroutine_function
    """
    try:
        from tornado.gen import is_coroutine_function

        result = is_coroutine_function(func)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_is_coroutine_function"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_is_coroutine_function"}


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
