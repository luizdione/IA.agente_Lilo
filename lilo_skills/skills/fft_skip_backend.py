"""
Skill: fft_skip_backend
Fonte: scipy.fft.skip_backend (scipy v1.15.3)
Complexidade: simple
Tags: estatistica, matematica
"""


def fft_skip_backend(backend: str):
    """
    Context manager to skip a backend within a fixed scope.

Within the context of a ``with`` statement, the given backend will not be
called. This covers backends registered both locally and globally. Upon
exit, the backend will again be considered.

Parameters
----------
backend : {object, 'scipy'}
  ...

    Args:
        backend: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.skip_backend
    """
    try:
        from scipy.fft import skip_backend

        result = skip_backend(backend)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_skip_backend"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_skip_backend"}


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
