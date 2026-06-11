"""
Skill: chart_quote_sheetname
Fonte: xlsxwriter.chart.quote_sheetname (xlsxwriter v3.2.9)
Complexidade: simple
Tags: geral
"""


def chart_quote_sheetname(sheetname: str):
    """
    Sheetnames used in references should be quoted if they contain any spaces,
special characters or if they look like a A1 or RC cell reference. The rules
are shown inline below.

Args:
   sheetname: The worksheet name. String.

Returns:
    A quoted worksheet string.

    Args:
        sheetname: str — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: xlsxwriter.chart.quote_sheetname
    """
    try:
        from xlsxwriter.chart import quote_sheetname

        result = quote_sheetname(sheetname)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "chart_quote_sheetname"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "chart_quote_sheetname"}


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
