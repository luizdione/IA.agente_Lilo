"""
Skill: gen_isawaitable
Fonte: tornado.gen.isawaitable (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def gen_isawaitable(object: str):
    """
    Return true if object can be passed to an ``await`` expression.

    Args:
        object: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.isawaitable
    """
    try:
        from tornado.gen import isawaitable

        result = isawaitable(object)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_isawaitable"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_isawaitable"}


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
