"""
Skill: gen_sleep
Fonte: tornado.gen.sleep (tornado v6.1)
Complexidade: simple
Tags: matematica
"""


def gen_sleep(duration: float):
    """
    Return a `.Future` that resolves after the given number of seconds.

When used with ``yield`` in a coroutine, this is a non-blocking
analogue to `time.sleep` (which should not be used in coroutines
because it is blocking)::

    yield gen.sleep(0.5)

Note that calling this function on its own does n...

    Args:
        duration: float — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.sleep
    """
    try:
        from tornado.gen import sleep

        result = sleep(duration)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_sleep"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_sleep"}


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
