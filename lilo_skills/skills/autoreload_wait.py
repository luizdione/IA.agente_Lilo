"""
Skill: autoreload_wait
Fonte: tornado.autoreload.wait (tornado v6.1)
Complexidade: simple
Tags: estatistica
"""


def autoreload_wait():
    """
    Wait for a watched file to change, then restart the process.

Intended to be used at the end of scripts like unit test runners,
to run the tests again after any source file changes (but see also
the command-line interface in `main`)

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.autoreload.wait
    """
    try:
        from tornado.autoreload import wait

        result = wait()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "autoreload_wait"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "autoreload_wait"}


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
