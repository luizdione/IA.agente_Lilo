"""
Skill: validators_add_metaclass
Fonte: jsonschema.validators.add_metaclass (jsonschema v3.2.0)
Complexidade: simple
Tags: geral
"""


def validators_add_metaclass(metaclass: str):
    """
    Class decorator for creating a class with a metaclass.

    Args:
        metaclass: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.validators.add_metaclass
    """
    try:
        from jsonschema.validators import add_metaclass

        result = add_metaclass(metaclass)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "validators_add_metaclass"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "validators_add_metaclass"}


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
