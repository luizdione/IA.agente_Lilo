"""
Skill: datasets_face
Fonte: scipy.datasets.face (scipy v1.15.3)
Complexidade: simple
Tags: visualizacao
"""


def datasets_face(gray: str = False):
    """
    Get a 1024 x 768, color image of a raccoon face.

The image is derived from
https://pixnio.com/fauna-animals/raccoons/raccoon-procyon-lotor

Parameters
----------
gray : bool, optional
    If True return 8-bit grey-scale image, otherwise return a color image

Returns
-------
face : ndarray
    image...

    Args:
        gray: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.datasets.face
    """
    try:
        from scipy.datasets import face

        result = face(gray)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "datasets_face"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "datasets_face"}


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
