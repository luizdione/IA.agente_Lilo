"""
Skill: mpmath_fib
Fonte: mpmath.fib (mpmath v1.3.0)
Complexidade: simple
Tags: matematica
"""


def mpmath_fib(x: str, kwargs: str):
    """
    ``fibonacci(n)`` computes the `n`-th Fibonacci number, `F(n)`. The
Fibonacci numbers are defined by the recurrence `F(n) = F(n-1) + F(n-2)`
with the initial values `F(0) = 0`, `F(1) = 1`. :func:`~mpmath.fibonacci`
extends this definition to arbitrary real and complex arguments
using the formula

.. ...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.fib
    """
    try:
        from mpmath import fib

        result = fib(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_fib"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_fib"}


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
