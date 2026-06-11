"""
Skill: gen_convert_yielded
Fonte: tornado.gen.convert_yielded (tornado v6.1)
Complexidade: simple
Tags: bioinformatica, manipulacao_dados
"""


def gen_convert_yielded(yielded: str):
    """
    Convert a yielded object into a `.Future`.

The default implementation accepts lists, dictionaries, and
Futures. This has the side effect of starting any coroutines that
did not start themselves, similar to `asyncio.ensure_future`.

If the `~functools.singledispatch` library is available, this funct...

    Args:
        yielded: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.convert_yielded
    """
    try:
        from tornado.gen import convert_yielded

        result = convert_yielded(yielded)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_convert_yielded"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_convert_yielded"}


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
