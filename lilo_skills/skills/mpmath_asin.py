"""
Skill: mpmath_asin
Fonte: mpmath.asin (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_asin(x: str, kwargs: str):
    """
    Computes the inverse sine or arcsine of `x`, `\sin^{-1}(x)`.
Since `-1 \le \sin(x) \le 1` for real `x`, the inverse
sine is real-valued only for `-1 \le x \le 1`.
On this interval, it is defined to be a monotonically increasing
function assuming values between `-\pi/2` and `\pi/2`.

Basic values are...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.asin
    """
    try:
        from mpmath import asin

        result = asin(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_asin"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_asin"}


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
