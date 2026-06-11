"""
Skill: fftpack_hilbert
Fonte: scipy.fftpack.hilbert (scipy v1.15.3)
Complexidade: simple
Tags: bioinformatica, manipulacao_dados, matematica
"""


def fftpack_hilbert(x: str, _cache: str = "<_thread._local object at 0x744f61cb2390>"):
    """
    Return Hilbert transform of a periodic sequence x.

If x_j and y_j are Fourier coefficients of periodic functions x
and y, respectively, then::

  y_j = sqrt(-1)*sign(j) * x_j
  y_0 = 0

Parameters
----------
x : array_like
    The input array, should be periodic.
_cache : dict, optional
    Diction...

    Args:
        x: Any — ver docstring original
        _cache: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fftpack.hilbert
    """
    try:
        from scipy.fftpack import hilbert

        result = hilbert(x, _cache)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fftpack_hilbert"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fftpack_hilbert"}


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
