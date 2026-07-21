"""
Skill: backend_bases_is_interactive
Fonte: matplotlib.backend_bases.is_interactive (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def backend_bases_is_interactive():
    """
    Return whether to redraw after every plotting command.

.. note::

    This function is only intended for use in backends. End users should
    use `.pyplot.isinteractive` instead.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.backend_bases.is_interactive
    """
    try:
        from matplotlib.backend_bases import is_interactive

        result = is_interactive()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "backend_bases_is_interactive"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "backend_bases_is_interactive"}


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
