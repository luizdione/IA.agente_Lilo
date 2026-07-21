"""
Skill: ctx_iv_mpi_from_str
Fonte: mpmath.ctx_iv.mpi_from_str (mpmath v1.3.0)
Complexidade: simple
Tags: manipulacao_dados
"""


def ctx_iv_mpi_from_str(s: str, prec: str):
    """
    Parse an interval number given as a string.

Allowed forms are

"-1.23e-27"
    Any single decimal floating-point literal.
"a +- b"  or  "a (b)"
    a is the midpoint of the interval and b is the half-width
"a +- b%"  or  "a (b%)"
    a is the midpoint of the interval and the half-width
    is b per...

    Args:
        s: Any — ver docstring original
        prec: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ctx_iv.mpi_from_str
    """
    try:
        from mpmath.ctx_iv import mpi_from_str

        result = mpi_from_str(s, prec)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "ctx_iv_mpi_from_str"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "ctx_iv_mpi_from_str"}


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
