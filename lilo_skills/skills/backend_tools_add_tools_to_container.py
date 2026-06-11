"""
Skill: backend_tools_add_tools_to_container
Fonte: matplotlib.backend_tools.add_tools_to_container (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def backend_tools_add_tools_to_container(container: str, tools: str = [['navigation', ['home', 'back', 'forward']], ['zoompan', ['pan', 'zoom', 'subplots']], ['io', ['save', 'help']]]):
    """
    Add multiple tools to the container.

Parameters
----------
container : Container
    `.backend_bases.ToolContainerBase` object that will get the tools
    added.
tools : list, optional
    List in the form ``[[group1, [tool1, tool2 ...]], [group2, [...]]]``
    where the tools ``[tool1, tool2, ...]...

    Args:
        container: Any — ver docstring original
        tools: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.backend_tools.add_tools_to_container
    """
    try:
        from matplotlib.backend_tools import add_tools_to_container

        result = add_tools_to_container(container, tools)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "backend_tools_add_tools_to_container"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "backend_tools_add_tools_to_container"}


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
