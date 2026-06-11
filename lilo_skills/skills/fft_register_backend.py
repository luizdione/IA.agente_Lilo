"""
Skill: fft_register_backend
Fonte: scipy.fft.register_backend (scipy v1.15.3)
Complexidade: simple
Tags: matematica
"""


def fft_register_backend(backend: str):
    """
    Register a backend for permanent use.

Registered backends have the lowest priority and will be tried after the
global backend.

Parameters
----------
backend : {object, 'scipy'}
    The backend to use.
    Can either be a ``str`` containing the name of a known backend
    {'scipy'} or an object tha...

    Args:
        backend: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.register_backend
    """
    try:
        from scipy.fft import register_backend

        result = register_backend(backend)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_register_backend"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_register_backend"}


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
