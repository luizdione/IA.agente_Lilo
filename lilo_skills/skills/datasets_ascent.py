"""
Skill: datasets_ascent
Fonte: scipy.datasets.ascent (scipy v1.15.3)
Complexidade: simple
Tags: estatistica, visualizacao
"""


def datasets_ascent():
    """
    Get an 8-bit grayscale bit-depth, 512 x 512 derived image for easy
use in demos.

The image is derived from
https://pixnio.com/people/accent-to-the-top

Parameters
----------
None

Returns
-------
ascent : ndarray
   convenient image to use for testing and demonstration

Examples
--------
>>> import...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.datasets.ascent
    """
    try:
        from scipy.datasets import ascent

        result = ascent()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "datasets_ascent"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "datasets_ascent"}


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
