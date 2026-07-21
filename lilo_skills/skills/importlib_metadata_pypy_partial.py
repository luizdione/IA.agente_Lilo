"""
Skill: importlib_metadata_pypy_partial
Fonte: importlib_metadata.pypy_partial (importlib-metadata v4.6.4)
Complexidade: simple
Tags: geral
"""


def importlib_metadata_pypy_partial(val: str):
    """
    Adjust for variable stacklevel on partial under PyPy.

Workaround for #327.

    Args:
        val: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.pypy_partial
    """
    try:
        from importlib_metadata import pypy_partial

        result = pypy_partial(val)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_pypy_partial"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_pypy_partial"}


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
