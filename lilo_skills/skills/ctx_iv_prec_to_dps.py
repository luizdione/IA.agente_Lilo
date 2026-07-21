"""
Skill: ctx_iv_prec_to_dps
Fonte: mpmath.ctx_iv.prec_to_dps (mpmath v1.3.0)
Complexidade: simple
Tags: machine_learning
"""


def ctx_iv_prec_to_dps(n: str):
    """
    Return number of accurate decimals that can be represented
with a precision of n bits.

    Args:
        n: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ctx_iv.prec_to_dps
    """
    try:
        from mpmath.ctx_iv import prec_to_dps

        result = prec_to_dps(n)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "ctx_iv_prec_to_dps"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "ctx_iv_prec_to_dps"}


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
