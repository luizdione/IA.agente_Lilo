"""
Skill: datasets_download_all
Fonte: scipy.datasets.download_all (scipy v1.15.3)
Complexidade: simple
Tags: manipulacao_dados
"""


def datasets_download_all(path: str = None):
    """
    Utility method to download all the dataset files
for `scipy.datasets` module.

Parameters
----------
path : str, optional
    Directory path to download all the dataset files.
    If None, default to the system cache_dir detected by pooch.

    Args:
        path: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: scipy.datasets.download_all
    """
    try:
        from scipy.datasets import download_all

        result = download_all(path)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "datasets_download_all"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "datasets_download_all"}


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
