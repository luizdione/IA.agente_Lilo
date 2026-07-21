"""
Skill: mpmath_exp
Fonte: mpmath.exp (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_exp(x: str, kwargs: str):
    r"""
    Computes the exponential function,

.. math ::

    \exp(x) = e^x = \sum_{k=0}^{\infty} \frac{x^k}{k!}.

For complex numbers, the exponential function also satisfies

.. math ::

    \exp(x+yi) = e^x (\cos y + i \sin y).

**Basic examples**

Some values of the exponential function::

    >>> from mp...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.exp
    """
    try:
        from mpmath import exp

        result = exp(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_exp"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_exp"}


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
