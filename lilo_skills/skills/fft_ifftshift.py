"""
Skill: fft_ifftshift
Fonte: scipy.fft.ifftshift (scipy v1.15.3)
Complexidade: simple
Tags: matematica
"""


def fft_ifftshift(x: str, axes: str = None):
    """
    The inverse of `fftshift`. Although identical for even-length `x`, the
functions differ by one sample for odd-length `x`.

Parameters
----------
x : array_like
    Input array.
axes : int or shape tuple, optional
    Axes over which to calculate.  Defaults to None, which shifts all axes.

Returns
--...

    Args:
        x: Any — ver docstring original
        axes: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.ifftshift
    """
    try:
        from scipy.fft import ifftshift

        result = ifftshift(x, axes)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_ifftshift"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_ifftshift"}


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
