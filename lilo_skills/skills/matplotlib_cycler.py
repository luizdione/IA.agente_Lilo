"""
Skill: matplotlib_cycler
Fonte: matplotlib.cycler (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def matplotlib_cycler(args: str, kwargs: str):
    """
    Create a `~cycler.Cycler` object much like :func:`cycler.cycler`,
but includes input validation.

Call signatures::

  cycler(cycler)
  cycler(label=values, label2=values2, ...)
  cycler(label, values)

Form 1 copies a given `~cycler.Cycler` object.

Form 2 creates a `~cycler.Cycler` which cycles ov...

    Args:
        args: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.cycler
    """
    try:
        from matplotlib import cycler

        result = cycler(args, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_cycler"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_cycler"}


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
