"""
Skill: matplotlib_set_loglevel
Fonte: matplotlib.set_loglevel (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_set_loglevel(level: str):
    """
    Configure Matplotlib's logging levels.

Matplotlib uses the standard library `logging` framework under the root
logger 'matplotlib'.  This is a helper function to:

- set Matplotlib's root logger level
- set the root logger handler's level, creating the handler
  if it does not exist yet

Typically,...

    Args:
        level: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.set_loglevel
    """
    try:
        from matplotlib import set_loglevel

        result = set_loglevel(level)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_set_loglevel"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_set_loglevel"}


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
