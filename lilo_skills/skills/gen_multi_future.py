"""
Skill: gen_multi_future
Fonte: tornado.gen.multi_future (tornado v6.1)
Complexidade: simple
Tags: bioinformatica
"""


def gen_multi_future(children: str, quiet_exceptions: str = []):
    """
    Wait for multiple asynchronous futures in parallel.

Since Tornado 6.0, this function is exactly the same as `multi`.

.. versionadded:: 4.0

.. versionchanged:: 4.2
   If multiple ``Futures`` fail, any exceptions after the first (which is
   raised) will be logged. Added the ``quiet_exceptions``
  ...

    Args:
        children: Union — ver docstring original
        quiet_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.multi_future
    """
    try:
        from tornado.gen import multi_future

        result = multi_future(children, quiet_exceptions)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_multi_future"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_multi_future"}


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
