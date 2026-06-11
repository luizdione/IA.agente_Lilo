"""
Skill: importlib_metadata_distribution
Fonte: importlib_metadata.distribution (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_distribution(distribution_name: str):
    """
    Get the ``Distribution`` instance for the named package.

:param distribution_name: The name of the distribution package as a string.
:return: A ``Distribution`` instance (or subclass thereof).

    Args:
        distribution_name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.distribution
    """
    try:
        from importlib_metadata import distribution

        result = distribution(distribution_name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_distribution"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_distribution"}


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
