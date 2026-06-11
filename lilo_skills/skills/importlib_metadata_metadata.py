"""
Skill: importlib_metadata_metadata
Fonte: importlib_metadata.metadata (importlib-metadata v4.6.4)
Complexidade: simple
Tags: manipulacao_dados
"""


def importlib_metadata_metadata(distribution_name: str):
    """
    Get the metadata for the named package.

:param distribution_name: The name of the distribution package to query.
:return: A PackageMetadata containing the parsed metadata.

    Args:
        distribution_name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.metadata
    """
    try:
        from importlib_metadata import metadata

        result = metadata(distribution_name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_metadata"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_metadata"}


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
