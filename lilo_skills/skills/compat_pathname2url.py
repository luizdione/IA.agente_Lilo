"""
Skill: compat_pathname2url
Fonte: jsonschema.compat.pathname2url (jsonschema v3.2.0)
Complexidade: simple
Tags: bioinformatica, quimica
"""


def compat_pathname2url(pathname: str):
    """
    OS-specific conversion from a file system path to a relative URL
of the 'file' scheme; not recommended for general use.

    Args:
        pathname: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.compat.pathname2url
    """
    try:
        from jsonschema.compat import pathname2url

        result = pathname2url(pathname)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "compat_pathname2url"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "compat_pathname2url"}


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
