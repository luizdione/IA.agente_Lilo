"""
Skill: pandas_set_eng_float_format
Fonte: pandas.set_eng_float_format (pandas v2.3.3)
Complexidade: simple
Tags: machine_learning
"""


def pandas_set_eng_float_format(accuracy: int = 3, use_eng_prefix: bool = False):
    """
    Format float representation in DataFrame with SI notation.

Parameters
----------
accuracy : int, default 3
    Number of decimal digits after the floating point.
use_eng_prefix : bool, default False
    Whether to represent a value with SI prefixes.

Returns
-------
None

Examples
--------
>>> df =...

    Args:
        accuracy: int — ver docstring original
        use_eng_prefix: bool — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: pandas.set_eng_float_format
    """
    try:
        from pandas import set_eng_float_format

        result = set_eng_float_format(accuracy, use_eng_prefix)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "pandas_set_eng_float_format"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "pandas_set_eng_float_format"}


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
