"""
Skill: gen_future_set_exc_info
Fonte: tornado.gen.future_set_exc_info (tornado v6.1)
Complexidade: simple
Tags: bioinformatica, estatistica, manipulacao_dados
"""


def gen_future_set_exc_info(future: str, exc_info: str):
    """
    Set the given ``exc_info`` as the `Future`'s exception.

Understands both `asyncio.Future` and the extensions in older
versions of Tornado to enable better tracebacks on Python 2.

.. versionadded:: 5.0

.. versionchanged:: 6.0

   If the future is already cancelled, this function is a no-op.
   (pr...

    Args:
        future: Union[futures.Future[_T], Future[_T]] — ver docstring original
        exc_info: Tuple — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.future_set_exc_info
    """
    try:
        from tornado.gen import future_set_exc_info

        result = future_set_exc_info(future, exc_info)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_future_set_exc_info"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_future_set_exc_info"}


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
