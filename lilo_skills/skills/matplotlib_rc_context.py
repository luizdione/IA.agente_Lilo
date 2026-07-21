"""
Skill: matplotlib_rc_context
Fonte: matplotlib.rc_context (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_rc_context(rc: str = None, fname: str = None):
    """
    Return a context manager for temporarily changing rcParams.

The :rc:`backend` will not be reset by the context manager.

rcParams changed both through the context manager invocation and
in the body of the context will be reset on context exit.

Parameters
----------
rc : dict
    The rcParams to te...

    Args:
        rc: Any — ver docstring original
        fname: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rc_context
    """
    try:
        from matplotlib import rc_context

        result = rc_context(rc, fname)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rc_context"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rc_context"}


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
