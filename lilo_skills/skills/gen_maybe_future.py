"""
Skill: gen_maybe_future
Fonte: tornado.gen.maybe_future (tornado v6.1)
Complexidade: simple
Tags: manipulacao_dados
"""


def gen_maybe_future(x: str):
    """
    Converts ``x`` into a `.Future`.

If ``x`` is already a `.Future`, it is simply returned; otherwise
it is wrapped in a new `.Future`.  This is suitable for use as
``result = yield gen.maybe_future(f())`` when you don't know whether
``f()`` returns a `.Future` or not.

.. deprecated:: 4.3
   This fun...

    Args:
        x: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.maybe_future
    """
    try:
        from tornado.gen import maybe_future

        result = maybe_future(x)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_maybe_future"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_maybe_future"}


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
