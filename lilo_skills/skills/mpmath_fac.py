"""
Skill: mpmath_fac
Fonte: mpmath.fac (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_fac(x: str, kwargs: str):
    r"""
    Computes the factorial, `x!`. For integers `n \ge 0`, we have
`n! = 1 \cdot 2 \cdots (n-1) \cdot n` and more generally the factorial
is defined for real or complex `x` by `x! = \Gamma(x+1)`.

**Examples**

Basic values and limits::

    >>> from mpmath import *
    >>> mp.dps = 15; mp.pretty = True
...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.fac
    """
    try:
        from mpmath import fac

        result = fac(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_fac"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_fac"}


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
