"""
Skill: matplotlib_get_configdir
Fonte: matplotlib.get_configdir (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_get_configdir():
    """
    Return the string path of the configuration directory.

The directory is chosen as follows:

1. If the MPLCONFIGDIR environment variable is supplied, choose that.
2. On Linux, follow the XDG specification and look first in
   ``$XDG_CONFIG_HOME``, if defined, or ``$HOME/.config``.  On other
   platf...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.get_configdir
    """
    try:
        from matplotlib import get_configdir

        result = get_configdir()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_get_configdir"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_get_configdir"}


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
