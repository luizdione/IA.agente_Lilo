"""
Skill: gen_singledispatch
Fonte: tornado.gen.singledispatch (tornado v6.1)
Complexidade: simple
Tags: bioinformatica, manipulacao_dados
"""


def gen_singledispatch(func: str):
    """
    Single-dispatch generic function decorator.

Transforms a function into a generic function, which can have different
behaviours depending upon the type of its first argument. The decorated
function acts as the default implementation, and additional
implementations can be registered using the registe...

    Args:
        func: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.singledispatch
    """
    try:
        from tornado.gen import singledispatch

        result = singledispatch(func)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_singledispatch"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_singledispatch"}


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
