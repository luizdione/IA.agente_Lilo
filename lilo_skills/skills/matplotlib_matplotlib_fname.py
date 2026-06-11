"""
Skill: matplotlib_matplotlib_fname
Fonte: matplotlib.matplotlib_fname (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_matplotlib_fname():
    """
    Get the location of the config file.

The file location is determined in the following order

- ``$PWD/matplotlibrc``
- ``$MATPLOTLIBRC`` if it is not a directory
- ``$MATPLOTLIBRC/matplotlibrc``
- ``$MPLCONFIGDIR/matplotlibrc``
- On Linux,
    - ``$XDG_CONFIG_HOME/matplotlib/matplotlibrc`` (if ``$X...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.matplotlib_fname
    """
    try:
        from matplotlib import matplotlib_fname

        result = matplotlib_fname()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_matplotlib_fname"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_matplotlib_fname"}


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
