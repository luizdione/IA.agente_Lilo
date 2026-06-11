"""
Skill: matplotlib_sanitize_sequence
Fonte: matplotlib.sanitize_sequence (matplotlib v3.10.8)
Complexidade: simple
Tags: bioinformatica, visualizacao
"""


def matplotlib_sanitize_sequence(data: str):
    """
    [*Deprecated*] 

Notes
-----
.. deprecated:: 3.10
   Use matplotlib.cbook.sanitize_sequence instead.\ 

    Args:
        data: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.sanitize_sequence
    """
    try:
        from matplotlib import sanitize_sequence

        result = sanitize_sequence(data)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_sanitize_sequence"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_sanitize_sequence"}


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
