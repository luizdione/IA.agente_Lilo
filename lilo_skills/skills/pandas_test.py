"""
Skill: pandas_test
Fonte: pandas.test (pandas v2.3.3)
Complexidade: simple
Tags: estatistica
"""


def pandas_test(extra_args: list = None, run_doctests: bool = False):
    """
    Run the pandas test suite using pytest.

By default, runs with the marks -m "not slow and not network and not db"

Parameters
----------
extra_args : list[str], default None
    Extra marks to run the tests.
run_doctests : bool, default False
    Whether to only run the Python and Cython doctests. I...

    Args:
        extra_args: list[str] | None — ver docstring original
        run_doctests: bool — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: pandas.test
    """
    try:
        from pandas import test

        result = test(extra_args, run_doctests)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "pandas_test"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "pandas_test"}


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
