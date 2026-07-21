"""
Skill: numpy_diag_indices
Fonte: numpy.diag_indices (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_diag_indices(n: str, ndim: str = 2):
    """
    Return the indices to access the main diagonal of an array.

This returns a tuple of indices that can be used to access the main
diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
(n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
``a.ndim > 2`` this is the set of ind...

    Args:
        n: Any — ver docstring original
        ndim: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.diag_indices
    """
    try:
        from numpy import diag_indices

        result = diag_indices(n, ndim)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_diag_indices"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_diag_indices"}


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
