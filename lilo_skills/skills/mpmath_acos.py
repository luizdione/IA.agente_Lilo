"""
Skill: mpmath_acos
Fonte: mpmath.acos (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_acos(x: str, kwargs: str):
    """
    Computes the inverse cosine or arccosine of `x`, `\cos^{-1}(x)`.
Since `-1 \le \cos(x) \le 1` for real `x`, the inverse
cosine is real-valued only for `-1 \le x \le 1`. On this interval,
:func:`~mpmath.acos` is defined to be a monotonically decreasing
function assuming values between `+\pi` and `0`....

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.acos
    """
    try:
        from mpmath import acos

        result = acos(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_acos"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_acos"}


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
