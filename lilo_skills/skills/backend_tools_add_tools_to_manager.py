"""
Skill: backend_tools_add_tools_to_manager
Fonte: matplotlib.backend_tools.add_tools_to_manager (matplotlib v3.10.8)
Complexidade: simple
Tags: geral
"""


def backend_tools_add_tools_to_manager(toolmanager: str, tools: str = "{'home': <class 'matplotlib.backend_tools.ToolHome'>, 'back': <class 'matplotlib.backend_tools.ToolBack'>, 'forward': <class 'matplotlib.backend_tools.ToolForward'>, 'zoom': <class 'matplotlib.backend_tools.ToolZoom'>, 'pan': <class 'matplotlib.backend_tools.ToolPan'>, 'subplots': <class 'matplotlib.backend_tools.ConfigureSubplotsBase'>, 'save': <class 'matplotlib.backend_tools.SaveFigureBase'>, 'grid': <class 'matplotlib.backend_tools.ToolGrid'>, 'grid_minor': <class 'matplotlib.backend_tools.ToolMinorGrid'>, 'fullscreen': <class 'matplotlib.backend_tools.ToolFullScreen'>, 'quit': <class 'matplotlib.backend_tools.ToolQuit'>, 'quit_all': <class 'matplotlib.backend_tools.ToolQuitAll'>, 'xscale': <class 'matplotlib.backend_tools.ToolXScale'>, 'yscale': <class 'matplotlib.backend_tools.ToolYScale'>, 'position': <class 'matplotlib.backend_tools.ToolCursorPosition'>, 'viewpos': <class 'matplotlib.backend_tools.ToolViewsPositions'>, 'cursor': <class 'matplotlib.backend_tools.ToolSetCursor'>, 'rubberband': <class 'matplotlib.backend_tools.RubberbandBase'>, 'help': <class 'matplotlib.backend_tools.ToolHelpBase'>, 'copy': <class 'matplotlib.backend_tools.ToolCopyToClipboardBase'>}"):
    """
    Add multiple tools to a `.ToolManager`.

Parameters
----------
toolmanager : `.backend_managers.ToolManager`
    Manager to which the tools are added.
tools : {str: class_like}, optional
    The tools to add in a {name: tool} dict, see
    `.backend_managers.ToolManager.add_tool` for more info.

    Args:
        toolmanager: Any — ver docstring original
        tools: Any — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.backend_tools.add_tools_to_manager
    """
    try:
        from matplotlib.backend_tools import add_tools_to_manager

        result = add_tools_to_manager(toolmanager, tools)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "backend_tools_add_tools_to_manager"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "backend_tools_add_tools_to_manager"}


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
