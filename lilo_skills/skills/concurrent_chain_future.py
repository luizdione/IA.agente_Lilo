"""
Skill: concurrent_chain_future
Fonte: tornado.concurrent.chain_future (tornado v6.1)
Complexidade: medium
Tags: bioinformatica, manipulacao_dados
"""


def concurrent_chain_future(a: str, b: str):
    """
    Chain two futures together so that when one completes, so does the other.

The result (success or failure) of ``a`` will be copied to ``b``, unless
``b`` has already been completed or cancelled by the time ``a`` finishes.

.. versionchanged:: 5.0

   Now accepts both Tornado/asyncio `Future` objects...

    Args:
        a: Future[_T] — ver docstring original
        b: Future[_T] — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.concurrent.chain_future
    """
    try:
        from tornado.concurrent import chain_future

        result = chain_future(a, b)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "concurrent_chain_future"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "concurrent_chain_future"}


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
