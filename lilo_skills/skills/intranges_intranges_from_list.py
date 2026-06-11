"""
Skill: intranges_intranges_from_list
Fonte: idna.intranges.intranges_from_list (idna v3.11)
Complexidade: simple
Tags: bioinformatica
"""


def intranges_intranges_from_list(list_: str):
    """
    Represent a list of integers as a sequence of ranges:
((start_0, end_0), (start_1, end_1), ...), such that the original
integers are exactly those x such that start_i <= x < end_i for some i.

Ranges are encoded as single integers (start << 32 | end), not as tuples.

    Args:
        list_: List — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: idna.intranges.intranges_from_list
    """
    try:
        from idna.intranges import intranges_from_list

        result = intranges_from_list(list_)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "intranges_intranges_from_list"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "intranges_intranges_from_list"}


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
