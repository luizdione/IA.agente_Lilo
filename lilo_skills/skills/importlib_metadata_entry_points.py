"""
Skill: importlib_metadata_entry_points
Fonte: importlib_metadata.entry_points (importlib-metadata v4.6.4)
Complexidade: simple
Tags: estatistica, manipulacao_dados
"""


def importlib_metadata_entry_points(params: str):
    """
    Return EntryPoint objects for all installed packages.

Pass selection parameters (group or name) to filter the
result to entry points matching those properties (see
EntryPoints.select()).

For compatibility, returns ``SelectableGroups`` object unless
selection parameters are supplied. In the future,...

    Args:
        params: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.entry_points
    """
    try:
        from importlib_metadata import entry_points

        result = entry_points(params)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_entry_points"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_entry_points"}


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
