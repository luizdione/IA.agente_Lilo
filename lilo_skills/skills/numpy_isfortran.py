"""
Skill: numpy_isfortran
Fonte: numpy.isfortran (numpy v2.2.6)
Complexidade: simple
Tags: estatistica
"""


def numpy_isfortran(a: str):
    """
    Check if the array is Fortran contiguous but *not* C contiguous.

This function is obsolete. If you only want to check if an array is Fortran
contiguous use ``a.flags.f_contiguous`` instead.

Parameters
----------
a : ndarray
    Input array.

Returns
-------
isfortran : bool
    Returns True if the...

    Args:
        a: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.isfortran
    """
    try:
        from numpy import isfortran

        result = isfortran(a)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_isfortran"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_isfortran"}


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
