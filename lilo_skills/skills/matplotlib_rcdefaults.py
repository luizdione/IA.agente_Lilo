"""
Skill: matplotlib_rcdefaults
Fonte: matplotlib.rcdefaults (matplotlib v3.10.8)
Complexidade: simple
Tags: bioinformatica, manipulacao_dados, visualizacao
"""


def matplotlib_rcdefaults():
    """
    Restore the `.rcParams` from Matplotlib's internal default style.

Style-blacklisted `.rcParams` (defined in
``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.

See Also
--------
matplotlib.rc_file_defaults
    Restore the `.rcParams` from the rc file originally loaded by
    Matplotlib.
ma...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rcdefaults
    """
    try:
        from matplotlib import rcdefaults

        result = rcdefaults()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rcdefaults"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rcdefaults"}


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
