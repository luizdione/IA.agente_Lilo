"""
Skill: mpmath_loggamma
Fonte: mpmath.loggamma (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_loggamma(x: str, kwargs: str):
    """
    Computes the principal branch of the log-gamma function,
`\ln \Gamma(z)`. Unlike `\ln(\Gamma(z))`, which has infinitely many
complex branch cuts, the principal log-gamma function only has a single
branch cut along the negative half-axis. The principal branch
continuously matches the asymptotic Stirl...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.loggamma
    """
    try:
        from mpmath import loggamma

        result = loggamma(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_loggamma"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_loggamma"}


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
