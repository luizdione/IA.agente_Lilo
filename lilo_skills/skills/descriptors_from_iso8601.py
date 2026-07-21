"""
Skill: descriptors_from_iso8601
Fonte: openpyxl.descriptors.from_ISO8601 (openpyxl v3.1.5)
Complexidade: simple
Tags: manipulacao_dados
"""


def descriptors_from_iso8601(formatted_string: str):
    """
    Convert from a timestamp string to a datetime object. According to
18.17.4 in the specification the following ISO 8601 formats are
supported.

Dates B.1.1 and B.2.1
Times B.1.2 and B.2.2
Datetimes B.1.3 and B.2.3

There is no concept of timedeltas in the specification, but Excel
writes them (in stri...

    Args:
        formatted_string: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: openpyxl.descriptors.from_ISO8601
    """
    try:
        from openpyxl.descriptors import from_ISO8601

        result = from_ISO8601(formatted_string)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "descriptors_from_iso8601"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "descriptors_from_iso8601"}


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
