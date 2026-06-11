"""
Skill: mpmath_ln
Fonte: mpmath.ln (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_ln(x: str, kwargs: str):
    """
    Computes the base-`b` logarithm of `x`, `\log_b(x)`. If `b` is
unspecified, :func:`~mpmath.log` computes the natural (base `e`) logarithm
and is equivalent to :func:`~mpmath.ln`. In general, the base `b` logarithm
is defined in terms of the natural logarithm as
`\log_b(x) = \ln(x)/\ln(b)`.

By conve...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ln
    """
    try:
        from mpmath import ln

        result = ln(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_ln"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_ln"}


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
