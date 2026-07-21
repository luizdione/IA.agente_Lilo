"""
Skill: matplotlib_validate_backend
Fonte: matplotlib.validate_backend (matplotlib v3.10.8)
Complexidade: simple
Tags: visualizacao
"""


def matplotlib_validate_backend(s: str):
    r"""
    [*Deprecated*] 

Notes
-----
.. deprecated:: 3.10
   Use matplotlib.rcsetup.validate_backend instead.\ 

    Args:
        s: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.validate_backend
    """
    try:
        from matplotlib import validate_backend

        result = validate_backend(s)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_validate_backend"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_validate_backend"}


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
