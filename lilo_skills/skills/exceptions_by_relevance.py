"""
Skill: exceptions_by_relevance
Fonte: jsonschema.exceptions.by_relevance (jsonschema v3.2.0)
Complexidade: simple
Tags: geral
"""


def exceptions_by_relevance(weak: str = "frozenset({'oneOf', 'anyOf'})", strong: str = "frozenset()"):
    """
    Create a key function that can be used to sort errors by relevance.

Arguments:
    weak (set):
        a collection of validator names to consider to be "weak".
        If there are two errors at the same level of the instance
        and one is in the set of weak validator names, the other
       ...

    Args:
        weak: Any — ver docstring original
        strong: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.exceptions.by_relevance
    """
    try:
        from jsonschema.exceptions import by_relevance

        result = by_relevance(weak, strong)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "exceptions_by_relevance"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "exceptions_by_relevance"}


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
