"""
Skill: mpmath_ei
Fonte: mpmath.ei (mpmath v1.3.0)
Complexidade: simple
Tags: bioinformatica, matematica
"""


def mpmath_ei(x: str, kwargs: str):
    r"""
    Computes the exponential integral or Ei-function, `\mathrm{Ei}(x)`.
The exponential integral is defined as

.. math ::

  \mathrm{Ei}(x) = \int_{-\infty\,}^x \frac{e^t}{t} \, dt.

When the integration range includes `t = 0`, the exponential
integral is interpreted as providing the Cauchy principal v...

    Args:
        x: Any — ver docstring original
        kwargs: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: mpmath.ei
    """
    try:
        from mpmath import ei

        result = ei(x, kwargs)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "mpmath_ei"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "mpmath_ei"}


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
