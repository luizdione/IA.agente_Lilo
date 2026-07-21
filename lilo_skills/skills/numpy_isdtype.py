"""
Skill: numpy_isdtype
Fonte: numpy.isdtype (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_isdtype(dtype: str, kind: str):
    """
    Determine if a provided dtype is of a specified data type ``kind``.

This function only supports built-in NumPy's data types.
Third-party dtypes are not yet supported.

Parameters
----------
dtype : dtype
    The input dtype.
kind : dtype or str or tuple of dtypes/strs.
    dtype or dtype kind. Allo...

    Args:
        dtype: Any — ver docstring original
        kind: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.isdtype
    """
    try:
        from numpy import isdtype

        result = isdtype(dtype, kind)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_isdtype"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_isdtype"}


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
