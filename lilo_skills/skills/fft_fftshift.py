"""
Skill: fft_fftshift
Fonte: scipy.fft.fftshift (scipy v1.15.3)
Complexidade: simple
Tags: matematica
"""


def fft_fftshift(x: str, axes: str = None):
    """
    Shift the zero-frequency component to the center of the spectrum.

This function swaps half-spaces for all axes listed (defaults to all).
Note that ``y[0]`` is the Nyquist component only if ``len(x)`` is even.

Parameters
----------
x : array_like
    Input array.
axes : int or shape tuple, optional...

    Args:
        x: Any — ver docstring original
        axes: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.fftshift
    """
    try:
        from scipy.fft import fftshift

        result = fftshift(x, axes)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_fftshift"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_fftshift"}


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
