"""
Skill: differentiate_array_namespace
Fonte: scipy.differentiate.array_namespace (scipy v1.15.3)
Complexidade: simple
Tags: bioinformatica
"""


def differentiate_array_namespace(arrays: str):
    """
    Get the array API compatible namespace for the arrays xs.

Parameters
----------
*arrays : sequence of array_like
    Arrays used to infer the common namespace.

Returns
-------
namespace : module
    Common namespace.

Notes
-----
Thin wrapper around `array_api_compat.array_namespace`.

1. Check fo...

    Args:
        arrays: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.differentiate.array_namespace
    """
    try:
        from scipy.differentiate import array_namespace

        result = array_namespace(arrays)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "differentiate_array_namespace"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "differentiate_array_namespace"}


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
