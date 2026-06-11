"""
Skill: matplotlib_rc_file_defaults
Fonte: matplotlib.rc_file_defaults (matplotlib v3.10.8)
Complexidade: simple
Tags: manipulacao_dados, visualizacao
"""


def matplotlib_rc_file_defaults():
    """
    Restore the `.rcParams` from the original rc file loaded by Matplotlib.

Style-blacklisted `.rcParams` (defined in
``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.rc_file_defaults
    """
    try:
        from matplotlib import rc_file_defaults

        result = rc_file_defaults()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_rc_file_defaults"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_rc_file_defaults"}


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
