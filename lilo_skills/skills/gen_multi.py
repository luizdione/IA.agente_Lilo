"""
Skill: gen_multi
Fonte: tornado.gen.Multi (tornado v6.1)
Complexidade: simple
Tags: estatistica, matematica
"""


def gen_multi(children: str, quiet_exceptions: str = []):
    """
    Runs multiple asynchronous operations in parallel.

``children`` may either be a list or a dict whose values are
yieldable objects. ``multi()`` returns a new yieldable
object that resolves to a parallel structure containing their
results. If ``children`` is a list, the result is a list of
results in...

    Args:
        children: Union — ver docstring original
        quiet_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.Multi
    """
    try:
        from tornado.gen import Multi

        result = Multi(children, quiet_exceptions)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_multi"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_multi"}


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
