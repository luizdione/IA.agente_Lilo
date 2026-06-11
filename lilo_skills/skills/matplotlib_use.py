"""
Skill: matplotlib_use
Fonte: matplotlib.use (matplotlib v3.10.8)
Complexidade: simple
Tags: manipulacao_dados, visualizacao
"""


def matplotlib_use(backend: str, force: str = True):
    """
    Select the backend used for rendering and GUI integration.

If pyplot is already imported, `~matplotlib.pyplot.switch_backend` is used
and if the new backend is different than the current backend, all Figures
will be closed.

Parameters
----------
backend : str
    The backend to switch to.  This ca...

    Args:
        backend: Any — ver docstring original
        force: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.use
    """
    try:
        from matplotlib import use

        result = use(backend, force)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_use"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_use"}


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
