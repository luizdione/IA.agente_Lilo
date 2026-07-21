"""
Skill: numpy_get_printoptions
Fonte: numpy.get_printoptions (numpy v2.2.6)
Complexidade: simple
Tags: machine_learning
"""


def numpy_get_printoptions():
    """
    Return the current print options.

Returns
-------
print_opts : dict
    Dictionary of current print options with keys

    - precision : int
    - threshold : int
    - edgeitems : int
    - linewidth : int
    - suppress : bool
    - nanstr : str
    - infstr : str
    - sign : str
    - formatter...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.get_printoptions
    """
    try:
        from numpy import get_printoptions

        result = get_printoptions()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_get_printoptions"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_get_printoptions"}


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
