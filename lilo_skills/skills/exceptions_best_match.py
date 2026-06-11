"""
Skill: exceptions_best_match
Fonte: jsonschema.exceptions.best_match (jsonschema v3.2.0)
Complexidade: simple
Tags: bioinformatica
"""


def exceptions_best_match(errors: str, key: str = "<function by_relevance.<locals>.relevance at 0x744f7a3dbbe0>"):
    """
    Try to find an error that appears to be the best match among given errors.

In general, errors that are higher up in the instance (i.e. for which
`ValidationError.path` is shorter) are considered better matches,
since they indicate "more" is wrong with the instance.

If the resulting match is either...

    Args:
        errors: Any — ver docstring original
        key: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.exceptions.best_match
    """
    try:
        from jsonschema.exceptions import best_match

        result = best_match(errors, key)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "exceptions_best_match"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "exceptions_best_match"}


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
