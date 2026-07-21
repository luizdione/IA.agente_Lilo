"""
Skill: numpy_geterrcall
Fonte: numpy.geterrcall (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_geterrcall():
    """
    Return the current callback function used on floating-point errors.

When the error handling for a floating-point error (one of "divide",
"over", "under", or "invalid") is set to 'call' or 'log', the function
that is called or the log instance that is written to is returned by
`geterrcall`. This fun...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.geterrcall
    """
    try:
        from numpy import geterrcall

        result = geterrcall()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_geterrcall"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_geterrcall"}


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
