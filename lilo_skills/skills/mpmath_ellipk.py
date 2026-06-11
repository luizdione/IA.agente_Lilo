"""
Skill: mpmath_ellipk
Fonte: mpmath.ellipk (mpmath v1.3.0)
Complexidade: simple
Tags: matematica, visualizacao
"""


def mpmath_ellipk(x: str, kwargs: str):
    """
    Evaluates the complete elliptic integral of the first kind,
`K(m)`, defined by

.. math ::

    K(m) = \int_0^{\pi/2} \frac{dt}{\sqrt{1-m \sin^2 t}} \, = \,
    \frac{\pi}{2} \,_2F_1\left(\frac{1}{2}, \frac{1}{2}, 1, m\right).

Note that the argument is the parameter `m = k^2`,
not the modulus `k` w...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ellipk
    """
    try:
        from mpmath import ellipk

        result = ellipk(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_ellipk"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_ellipk"}


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
