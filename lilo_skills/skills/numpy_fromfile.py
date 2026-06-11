"""
Skill: numpy_fromfile
Fonte: numpy.fromfile (numpy v2.2.6)
Complexidade: simple
Tags: manipulacao_dados
"""


def numpy_fromfile(args: str):
    """
    fromfile(file, dtype=float, count=-1, sep='', offset=0, *, like=None)

Construct an array from data in a text or binary file.

A highly efficient way of reading binary data with a known data-type,
as well as parsing simply formatted text files.  Data written using the
`tofile` method can be read usi...

    Args:
        args: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.fromfile
    """
    try:
        from numpy import fromfile

        result = fromfile(args)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_fromfile"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_fromfile"}


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
