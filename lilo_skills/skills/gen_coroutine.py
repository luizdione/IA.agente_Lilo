"""
Skill: gen_coroutine
Fonte: tornado.gen.coroutine (tornado v6.1)
Complexidade: simple
Tags: bioinformatica
"""


def gen_coroutine(func: str):
    """
    Decorator for asynchronous generators.

For compatibility with older versions of Python, coroutines may
also "return" by raising the special exception `Return(value)
<Return>`.

Functions with this decorator return a `.Future`.

.. warning::

   When exceptions occur inside a coroutine, the exceptio...

    Args:
        func: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.coroutine
    """
    try:
        from tornado.gen import coroutine

        result = coroutine(func)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_coroutine"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_coroutine"}


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
