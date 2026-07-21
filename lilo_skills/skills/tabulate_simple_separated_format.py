"""
Skill: tabulate_simple_separated_format
Fonte: tabulate.simple_separated_format (tabulate v0.10.0)
Complexidade: simple
Tags: geral
"""


def tabulate_simple_separated_format(separator: str):
    """
    Construct a simple TableFormat with columns separated by a separator.

>>> tsv = simple_separated_format("\t") ;         tabulate([["foo", 1], ["spam", 23]], tablefmt=tsv) == 'foo \t 1\nspam\t23'
True

    Args:
        separator: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tabulate.simple_separated_format
    """
    try:
        from tabulate import simple_separated_format

        result = simple_separated_format(separator)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "tabulate_simple_separated_format"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "tabulate_simple_separated_format"}


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
