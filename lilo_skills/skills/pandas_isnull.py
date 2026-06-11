"""
Skill: pandas_isnull
Fonte: pandas.isnull (pandas v2.3.3)
Complexidade: simple
Tags: geral
"""


def pandas_isnull(obj: str):
    """
    Detect missing values for an array-like object.

This function takes a scalar or array-like object and indicates
whether values are missing (``NaN`` in numeric arrays, ``None`` or ``NaN``
in object arrays, ``NaT`` in datetimelike).

Parameters
----------
obj : scalar or array-like
    Object to chec...

    Args:
        obj: object — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: pandas.isnull
    """
    try:
        from pandas import isnull

        result = isnull(obj)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "pandas_isnull"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "pandas_isnull"}


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
