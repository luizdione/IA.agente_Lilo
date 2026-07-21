"""
Skill: fft_get_workers
Fonte: scipy.fft.get_workers (scipy v1.15.3)
Complexidade: simple
Tags: matematica
"""


def fft_get_workers():
    """
    Returns the default number of workers within the current context

Examples
--------
>>> from scipy import fft
>>> fft.get_workers()
1
>>> with fft.set_workers(4):
...     fft.get_workers()
4

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.fft.get_workers
    """
    try:
        from scipy.fft import get_workers

        result = get_workers()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "fft_get_workers"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "fft_get_workers"}


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
