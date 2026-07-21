"""
Skill: importlib_metadata_requires
Fonte: importlib_metadata.requires (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_requires(distribution_name: str):
    """
    Return a list of requirements for the named package.

:return: An iterator of requirements, suitable for
    packaging.requirement.Requirement.

    Args:
        distribution_name: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.requires
    """
    try:
        from importlib_metadata import requires

        result = requires(distribution_name)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_requires"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_requires"}


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
