"""
Skill: validators_validates
Fonte: jsonschema.validators.validates (jsonschema v3.2.0)
Complexidade: simple
Tags: quimica
"""


def validators_validates(version: str):
    """
    Register the decorated validator for a ``version`` of the specification.

Registered validators and their meta schemas will be considered when
parsing ``$schema`` properties' URIs.

Arguments:

    version (str):

        An identifier to use as the version's name

Returns:

    collections.Callable...

    Args:
        version: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.validators.validates
    """
    try:
        from jsonschema.validators import validates

        result = validates(version)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "validators_validates"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "validators_validates"}


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
