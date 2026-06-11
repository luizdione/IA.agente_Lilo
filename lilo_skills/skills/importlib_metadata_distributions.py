"""
Skill: importlib_metadata_distributions
Fonte: importlib_metadata.distributions (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_distributions(kwargs: str):
    """
    Get all ``Distribution`` instances in the current environment.

:return: An iterable of ``Distribution`` instances.

    Args:
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.distributions
    """
    try:
        from importlib_metadata import distributions

        result = distributions(kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_distributions"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_distributions"}


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
