"""
Skill: gen_overload
Fonte: tornado.gen.overload (tornado v6.1)
Complexidade: simple
Tags: manipulacao_dados
"""


def gen_overload(func: str):
    """
    Decorator for overloaded functions/methods.

In a stub file, place two or more stub definitions for the same
function in a row, each decorated with @overload.  For example:

  @overload
  def utf8(value: None) -> None: ...
  @overload
  def utf8(value: bytes) -> bytes: ...
  @overload
  def utf8(val...

    Args:
        func: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: tornado.gen.overload
    """
    try:
        from tornado.gen import overload

        result = overload(func)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "gen_overload"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "gen_overload"}


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
