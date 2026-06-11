"""
Skill: pandas_notna
Fonte: pandas.notna (pandas v2.3.3)
Complexidade: simple
Tags: geral
"""


def pandas_notna(obj: str):
    """
    Detect non-missing values for an array-like object.

This function takes a scalar or array-like object and indicates
whether values are valid (not missing, which is ``NaN`` in numeric
arrays, ``None`` or ``NaN`` in object arrays, ``NaT`` in datetimelike).

Parameters
----------
obj : array-like or o...

    Args:
        obj: object — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: pandas.notna
    """
    try:
        from pandas import notna

        result = notna(obj)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "pandas_notna"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "pandas_notna"}


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
