"""
Skill: importlib_metadata_method_cache
Fonte: importlib_metadata.method_cache (importlib-metadata v4.6.4)
Complexidade: simple
Tags: bioinformatica, machine_learning, manipulacao_dados
"""


def importlib_metadata_method_cache(method: str, cache_wrapper: str = None):
    """
    Wrap lru_cache to support storing the cache data in the object instances.

Abstracts the common paradigm where the method explicitly saves an
underscore-prefixed protected property on first call and returns that
subsequently.

>>> class MyClass:
...     calls = 0
...
...     @method_cache
...     de...

    Args:
        method: Any — ver docstring original
        cache_wrapper: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: importlib_metadata.method_cache
    """
    try:
        from importlib_metadata import method_cache

        result = method_cache(method, cache_wrapper)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "importlib_metadata_method_cache"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "importlib_metadata_method_cache"}


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
