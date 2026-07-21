"""
Skill: matplotlib_rc_params
Fonte: matplotlib.rc_params (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_rc_params(fail_on_error: str = False):
    """
    Construct a `RcParams` instance from the default Matplotlib rc file.

    Args:
        fail_on_error: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rc_params
    """
    try:
        from matplotlib import rc_params

        result = rc_params(fail_on_error)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rc_params"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rc_params"}


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
