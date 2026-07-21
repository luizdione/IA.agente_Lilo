"""
Skill: ctx_iv_dps_to_prec
Fonte: mpmath.ctx_iv.dps_to_prec (mpmath v1.3.0)
Complexidade: simple
Tags: geral
"""


def ctx_iv_dps_to_prec(n: str):
    """
    Return the number of bits required to represent n decimals
accurately.

    Args:
        n: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ctx_iv.dps_to_prec
    """
    try:
        from mpmath.ctx_iv import dps_to_prec

        result = dps_to_prec(n)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "ctx_iv_dps_to_prec"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "ctx_iv_dps_to_prec"}


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
