"""
Skill: validators_validator_for
Fonte: jsonschema.validators.validator_for (jsonschema v3.2.0)
Complexidade: simple
Tags: estatistica, quimica
"""


def validators_validator_for(schema: str, default: str = "<class 'jsonschema.validators.create.<locals>.Validator'>"):
    """
    Retrieve the validator class appropriate for validating the given schema.

Uses the :validator:`$schema` property that should be present in the
given schema to look up the appropriate validator class.

Arguments:

    schema (collections.Mapping or bool):

        the schema to look at

    default:...

    Args:
        schema: Any — ver docstring original
        default: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.validators.validator_for
    """
    try:
        from jsonschema.validators import validator_for

        result = validator_for(schema, default)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "validators_validator_for"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "validators_validator_for"}


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
