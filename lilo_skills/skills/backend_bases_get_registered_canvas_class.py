"""
Skill: backend_bases_get_registered_canvas_class
Fonte: matplotlib.backend_bases.get_registered_canvas_class (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def backend_bases_get_registered_canvas_class(format: str):
    """
    Return the registered default canvas for given file format.
Handles deferred import of required backend.

    Args:
        format: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.backend_bases.get_registered_canvas_class
    """
    try:
        from matplotlib.backend_bases import get_registered_canvas_class

        result = get_registered_canvas_class(format)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "backend_bases_get_registered_canvas_class"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "backend_bases_get_registered_canvas_class"}


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
