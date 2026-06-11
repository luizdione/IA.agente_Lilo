"""
Skill: importlib_metadata_install
Fonte: importlib_metadata.install (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_install():
    """
    Class decorator for installation on sys.meta_path.

Adds the backport DistributionFinder to sys.meta_path and
attempts to disable the finder functionality of the stdlib
DistributionFinder.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.install
    """
    try:
        from importlib_metadata import install

        result = install()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_install"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_install"}


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
