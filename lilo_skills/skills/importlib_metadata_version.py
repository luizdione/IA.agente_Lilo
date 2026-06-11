"""
Skill: importlib_metadata_version
Fonte: importlib_metadata.version (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_version(distribution_name: str):
    """
    Get the version string for the named package.

:param distribution_name: The name of the distribution package to query.
:return: The version string for the package as defined in the package's
    "Version" metadata key.

    Args:
        distribution_name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.version
    """
    try:
        from importlib_metadata import version

        result = version(distribution_name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_version"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_version"}


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
