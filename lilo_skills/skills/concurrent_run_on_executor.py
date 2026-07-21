"""
Skill: concurrent_run_on_executor
Fonte: tornado.concurrent.run_on_executor (tornado v6.1)
Complexidade: simple
Tags: bioinformatica, manipulacao_dados
"""


def concurrent_run_on_executor(args: str, kwargs: str):
    """
    Decorator to run a synchronous method asynchronously on an executor.

Returns a future.

The executor to be used is determined by the ``executor``
attributes of ``self``. To use a different attribute name, pass a
keyword argument to the decorator::

    @run_on_executor(executor='_thread_pool')
    ...

    Args:
        args: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.concurrent.run_on_executor
    """
    try:
        from tornado.concurrent import run_on_executor

        result = run_on_executor(args, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "concurrent_run_on_executor"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "concurrent_run_on_executor"}


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
