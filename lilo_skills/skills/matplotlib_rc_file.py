"""
Skill: matplotlib_rc_file
Fonte: matplotlib.rc_file (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_rc_file(fname: str, use_default_template: str = True):
    """
    Update `.rcParams` from file.

Style-blacklisted `.rcParams` (defined in
``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.

Parameters
----------
fname : str or path-like
    A file with Matplotlib rc settings.

use_default_template : bool
    If True, initialize with default parameters be...

    Args:
        fname: Any — ver docstring original
        use_default_template: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rc_file
    """
    try:
        from matplotlib import rc_file

        result = rc_file(fname, use_default_template)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rc_file"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rc_file"}


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
