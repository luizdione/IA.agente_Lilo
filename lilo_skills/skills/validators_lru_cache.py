"""
Skill: validators_lru_cache
Fonte: jsonschema.validators.lru_cache (jsonschema v3.2.0)
Complexidade: simple
Tags: estatistica, machine_learning
"""


def validators_lru_cache(maxsize: str = 128, typed: str = False):
    """
    Least-recently-used cache decorator.

If *maxsize* is set to None, the LRU features are disabled and the cache
can grow without bound.

If *typed* is True, arguments of different types will be cached separately.
For example, f(3.0) and f(3) will be treated as distinct calls with
distinct results.

A...

    Args:
        maxsize: Any — ver docstring original
        typed: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: jsonschema.validators.lru_cache
    """
    try:
        from jsonschema.validators import lru_cache

        result = lru_cache(maxsize, typed)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "validators_lru_cache"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "validators_lru_cache"}


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
