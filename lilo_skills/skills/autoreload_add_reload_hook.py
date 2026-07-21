"""
Skill: autoreload_add_reload_hook
Fonte: tornado.autoreload.add_reload_hook (tornado v6.1)
Complexidade: medium
Tags: bioinformatica, manipulacao_dados
"""


def autoreload_add_reload_hook(fn: str):
    """
    Add a function to be called before reloading the process.

Note that for open file and socket handles it is generally
preferable to set the ``FD_CLOEXEC`` flag (using `fcntl` or
`os.set_inheritable`) instead of using a reload hook to close them.

    Args:
        fn: Callable — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.autoreload.add_reload_hook
    """
    try:
        from tornado.autoreload import add_reload_hook

        result = add_reload_hook(fn)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "autoreload_add_reload_hook"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "autoreload_add_reload_hook"}


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
