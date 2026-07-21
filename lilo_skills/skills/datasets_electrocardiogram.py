"""
Skill: datasets_electrocardiogram
Fonte: scipy.datasets.electrocardiogram (scipy v1.15.3)
Complexidade: simple
Tags: manipulacao_dados
"""


def datasets_electrocardiogram():
    """
    Load an electrocardiogram as an example for a 1-D signal.

The returned signal is a 5 minute long electrocardiogram (ECG), a medical
recording of the heart's electrical activity, sampled at 360 Hz.

Returns
-------
ecg : ndarray
    The electrocardiogram in millivolt (mV) sampled at 360 Hz.

Notes
-...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.datasets.electrocardiogram
    """
    try:
        from scipy.datasets import electrocardiogram

        result = electrocardiogram()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "datasets_electrocardiogram"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "datasets_electrocardiogram"}


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
