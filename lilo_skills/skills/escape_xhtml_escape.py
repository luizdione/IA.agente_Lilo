"""
Skill: escape_xhtml_escape
Fonte: tornado.escape.xhtml_escape (tornado v6.1)
Complexidade: simple
Tags: geral
"""


def escape_xhtml_escape(value: str):
    """
    Escapes a string so it is valid within HTML or XML.

Escapes the characters ``<``, ``>``, ``"``, ``'``, and ``&``.
When used in attribute values the escaped strings must be enclosed
in quotes.

.. versionchanged:: 3.2

   Added the single quote to the list of escaped characters.

    Args:
        value: Union — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.escape.xhtml_escape
    """
    try:
        from tornado.escape import xhtml_escape

        result = xhtml_escape(value)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "escape_xhtml_escape"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "escape_xhtml_escape"}


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
