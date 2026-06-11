"""
Skill: scipy_show_config
Fonte: scipy.show_config (scipy v1.15.3)
Complexidade: simple
Tags: manipulacao_dados
"""


def scipy_show_config(mode: str = "stdout"):
    """
    Show libraries and system information on which SciPy was built
and is being used

Parameters
----------
mode : {`'stdout'`, `'dicts'`}, optional.
    Indicates how to display the config information.
    `'stdout'` prints to console, `'dicts'` returns a dictionary
    of the configuration.

Returns
-...

    Args:
        mode: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.show_config
    """
    try:
        from scipy import show_config

        result = show_config(mode)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "scipy_show_config"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "scipy_show_config"}


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
