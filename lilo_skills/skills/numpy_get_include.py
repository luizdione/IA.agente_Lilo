"""
Skill: numpy_get_include
Fonte: numpy.get_include (numpy v2.2.6)
Complexidade: simple
Tags: geral
"""


def numpy_get_include():
    r"""
    Return the directory that contains the NumPy \*.h header files.

Extension modules that need to compile against NumPy may need to use this
function to locate the appropriate include directory.

Notes
-----
When using ``setuptools``, for example in ``setup.py``::

    import numpy as np
    ...
    E...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: numpy.get_include
    """
    try:
        from numpy import get_include

        result = get_include()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "numpy_get_include"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "numpy_get_include"}


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
