"""
Skill: importlib_metadata_files
Fonte: importlib_metadata.files (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_files(distribution_name: str):
    """
    Return a list of files for the named package.

:param distribution_name: The name of the distribution package to query.
:return: List of files composing the distribution.

    Args:
        distribution_name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.files
    """
    try:
        from importlib_metadata import files

        result = files(distribution_name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_files"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_files"}


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
