"""
Skill: cli_namedany
Fonte: jsonschema.cli.namedAny (jsonschema v3.2.0)
Complexidade: simple
Tags: bioinformatica
"""


def cli_namedany(name: str):
    """
    Retrieve a Python object by its fully qualified name from the global Python
module namespace.  The first part of the name, that describes a module,
will be discovered and imported.  Each subsequent part of the name is
treated as the name of an attribute of the object specified by all of the
name whi...

    Args:
        name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.cli.namedAny
    """
    try:
        from jsonschema.cli import namedAny

        result = namedAny(name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "cli_namedany"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "cli_namedany"}


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
