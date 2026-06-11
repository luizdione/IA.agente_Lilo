"""
Skill: matplotlib_parse_version
Fonte: matplotlib.parse_version (matplotlib v3.10.8)
Complexidade: simple
Tags: manipulacao_dados
"""


def matplotlib_parse_version(version: str):
    """
    Parse the given version string.

>>> parse('1.0.dev1')
<Version('1.0.dev1')>

:param version: The version string to parse.
:raises InvalidVersion: When the version string is not a valid version.

    Args:
        version: str — ver docstring original

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: matplotlib.parse_version
    """
    try:
        from matplotlib import parse_version

        result = parse_version(version)

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {"error": f"Módulo não disponível: {e}", "skill": "matplotlib_parse_version"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "skill": "matplotlib_parse_version"}


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
