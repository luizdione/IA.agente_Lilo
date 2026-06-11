"""
Skill: pandas_show_versions
Fonte: pandas.show_versions (pandas v2.3.3)
Complexidade: medium
Tags: manipulacao_dados
"""


def pandas_show_versions(as_json: str = False):
    """
    Provide useful information, important for bug reports.

It comprises info about hosting operation system, pandas version,
and versions of other installed relative packages.

Parameters
----------
as_json : str or bool, default False
    * If False, outputs info in a human readable form to the consol...

    Args:
        as_json: str | bool — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: pandas.show_versions
    """
    try:
        from pandas import show_versions

        result = show_versions(as_json)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "pandas_show_versions"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "pandas_show_versions"}


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
