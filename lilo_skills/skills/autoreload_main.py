"""
Skill: autoreload_main
Fonte: tornado.autoreload.main (tornado v6.1)
Complexidade: simple
Tags: bioinformatica, estatistica, manipulacao_dados
"""


def autoreload_main():
    """
    Command-line wrapper to re-run a script whenever its source changes.

Scripts may be specified by filename or module name::

    python -m tornado.autoreload -m tornado.test.runtests
    python -m tornado.autoreload tornado/test/runtests.py

Running a script with this wrapper is similar to calling
`...

    Args:
        (sem parâmetros)

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.autoreload.main
    """
    try:
        from tornado.autoreload import main

        result = main()

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "autoreload_main"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "autoreload_main"}


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
