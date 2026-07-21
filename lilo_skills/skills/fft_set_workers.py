"""
Skill: fft_set_workers
Fonte: scipy.fft.set_workers (scipy v1.15.3)
Complexidade: simple
Tags: matematica
"""


def fft_set_workers(workers: str):
    """
    Context manager for the default number of workers used in `scipy.fft`

Parameters
----------
workers : int
    The default number of workers to use

Examples
--------
>>> import numpy as np
>>> from scipy import fft, signal
>>> rng = np.random.default_rng()
>>> x = rng.standard_normal((128, 64))
>>>...

    Args:
        workers: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.set_workers
    """
    try:
        from scipy.fft import set_workers

        result = set_workers(workers)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_set_workers"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_set_workers"}


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
