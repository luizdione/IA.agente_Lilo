"""
Skill: mpmath_runtests
Fonte: mpmath.runtests (mpmath v1.3.0)
Complexidade: simple
Tags: estatistica, matematica
"""


def mpmath_runtests():
    """
    Run all mpmath tests and print output.

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.runtests
    """
    try:
        from mpmath import runtests

        result = runtests()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_runtests"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_runtests"}


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
