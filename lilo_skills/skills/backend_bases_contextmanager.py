"""
Skill: backend_bases_contextmanager
Fonte: matplotlib.backend_bases.contextmanager (matplotlib v3.10.8)
Complexidade: simple
Tags: bioinformatica
"""


def backend_bases_contextmanager(func: str):
    """
    @contextmanager decorator.

Typical usage:

    @contextmanager
    def some_generator(<arguments>):
        <setup>
        try:
            yield <value>
        finally:
            <cleanup>

This makes this:

    with some_generator(<arguments>) as <variable>:
        <body>

equivalent to this...

    Args:
        func: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.backend_bases.contextmanager
    """
    try:
        from matplotlib.backend_bases import contextmanager

        result = contextmanager(func)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "backend_bases_contextmanager"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "backend_bases_contextmanager"}


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
