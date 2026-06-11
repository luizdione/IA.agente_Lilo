"""
Skill: mpmath_bernfrac
Fonte: mpmath.bernfrac (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_bernfrac(n: str):
    """
    Returns a tuple of integers `(p, q)` such that `p/q = B_n` exactly,
where `B_n` denotes the `n`-th Bernoulli number. The fraction is
always reduced to lowest terms. Note that for `n > 1` and `n` odd,
`B_n = 0`, and `(0, 1)` is returned.

**Examples**

The first few Bernoulli numbers are exactly::

 ...

    Args:
        n: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.bernfrac
    """
    try:
        from mpmath import bernfrac

        result = bernfrac(n)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_bernfrac"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_bernfrac"}


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
