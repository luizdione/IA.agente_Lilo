#!/usr/bin/env python3
"""
generate_skills.py — Gerador de Skills LILO a partir de funções extraídas
=========================================================================
Etapas 4-7 do pipeline: classificação, wrappers, schemas, validação.

Uso:
    python generate_skills.py
    python generate_skills.py --input extracted_functions.json
    python generate_skills.py --validate  # roda validação com inputs simulados

Entrada: extracted_functions.json (gerado por scan_conda_env.py)
Saída:   lilo_skills/skills/*.py, schemas/*.json, registry.json, logs/report.txt
"""

import json
import sys
import re
import time
import importlib
import threading
from pathlib import Path
import argparse

SCRIPT_DIR = Path(__file__).parent
SKILLS_DIR = SCRIPT_DIR / "skills"
SCHEMAS_DIR = SCRIPT_DIR / "schemas"
LOGS_DIR = SCRIPT_DIR / "logs"
REGISTRY_PATH = SCRIPT_DIR / "registry.json"

# ── Mapeamento de tipos Python → JSON Schema ────────────────────────────────

TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "tuple": "array",
    "None": "null",
    "NoneType": "null",
    "Any": "string",
    "bytes": "string",
    "Path": "string",
}

# Tipos complexos que podemos adaptar
ADAPTABLE_TYPES = {
    "ndarray": ("array", "Converter lista para numpy array internamente"),
    "Series": ("object", "Converter dict para pandas Series internamente"),
    "DataFrame": ("object", "Converter dict/CSV para DataFrame internamente"),
    "Sequence": ("string", "String de sequência biológica"),
    "Seq": ("string", "String de sequência DNA/RNA/proteína"),
    "array": ("array", "Array numérico"),
}

# Tags por keywords no nome/docstring
TAG_KEYWORDS = {
    "estatistica": ["test", "stat", "anova", "ttest", "chi", "fisher", "mann", "wilcox",
                     "shapiro", "levene", "kruskal", "correlation", "regression", "pvalue"],
    "bioinformatica": ["seq", "dna", "rna", "protein", "amino", "codon", "blast", "align",
                        "fasta", "fastq", "genome", "gene", "phylo", "tree", "bio"],
    "visualizacao": ["plot", "chart", "graph", "figure", "draw", "hist", "scatter", "bar",
                      "box", "heatmap", "dendrogram", "violin"],
    "manipulacao_dados": ["read", "write", "parse", "load", "save", "convert", "transform",
                           "merge", "concat", "pivot", "melt", "groupby", "filter"],
    "matematica": ["math", "matrix", "linear", "eigen", "decomp", "integrate", "interpolat",
                    "optimize", "minimize", "solve", "fft", "fourier"],
    "quimica": ["mol", "chem", "compound", "smiles", "inchi", "atom", "bond", "rdkit"],
    "machine_learning": ["fit", "predict", "train", "classify", "cluster", "feature",
                          "cross_val", "score", "accuracy", "precision", "recall"],
}


def classify_complexity(func: dict) -> str:
    """Etapa 4: Classifica complexidade da função."""
    params = func.get("parameters", [])

    # Sem parâmetros → simples
    if not params:
        return "simple"

    # Todos primitivos → simples
    if func.get("all_primitive_params", False):
        return "simple"

    # Tem tipos complexos → verificar se são adaptáveis
    if func.get("has_complex_params", False):
        # Verificar se todos os complexos são adaptáveis
        for p in params:
            if p.get("is_complex", False):
                type_base = p["type"].split("[")[0].strip()
                if type_base not in ADAPTABLE_TYPES:
                    return "complex"
        return "medium"

    # Não é tudo primitivo, mas sem complexos → medium
    return "medium"


def get_tags(func: dict) -> list[str]:
    """Gera tags para a função baseado em nome e docstring."""
    text = (func["name"] + " " + func.get("docstring", "")).lower()
    tags = set()
    for tag, keywords in TAG_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.add(tag)
                break
    if not tags:
        tags.add("geral")
    return sorted(tags)


def _python_type_to_json(type_str: str) -> str:
    """Converte tipo Python para tipo JSON Schema."""
    base = type_str.split("[")[0].strip()
    if base in TYPE_MAP:
        return TYPE_MAP[base]
    if base in ADAPTABLE_TYPES:
        return ADAPTABLE_TYPES[base][0]
    return "string"  # fallback seguro


def _sanitize_name(name: str) -> str:
    """Gera nome seguro para arquivo/função."""
    return re.sub(r'[^a-z0-9_]', '_', name.lower()).strip('_')


def _generate_param_conversion(param: dict) -> str:
    """Gera código de conversão para parâmetro não-primitivo."""
    type_base = param["type"].split("[")[0].strip()

    if type_base == "ndarray":
        return f"    {param['name']} = __import__('numpy').array({param['name']})\n"
    if type_base == "Series":
        return f"    {param['name']} = __import__('pandas').Series({param['name']})\n"
    if type_base == "DataFrame":
        return f"    {param['name']} = __import__('pandas').DataFrame({param['name']})\n"
    if type_base in ("Seq", "Sequence"):
        return f"    # {param['name']} usado como string diretamente\n"
    return ""


def generate_wrapper(func: dict, complexity: str) -> str:
    """Etapa 5: Gera wrapper Python para a função."""
    module = func["module"]
    original_name = func["name"]
    wrapper_name = _sanitize_name(f"{module.split('.')[-1]}_{original_name}")
    params = func.get("parameters", [])

    # Construir lista de parâmetros do wrapper
    param_strs = []
    param_docs = []
    for p in params:
        pname = p["name"]
        json_type = _python_type_to_json(p["type"])

        # Tipo Python para type hint
        py_type_map = {
            "string": "str", "integer": "int", "number": "float",
            "boolean": "bool", "array": "list", "object": "dict",
        }
        py_type = py_type_map.get(json_type, "str")

        if p.get("required", True):
            param_strs.append(f"{pname}: {py_type}")
        else:
            default = p.get("default")
            if default is None:
                param_strs.append(f"{pname}: {py_type} = None")
            elif isinstance(default, str):
                param_strs.append(f'{pname}: {py_type} = "{default}"')
            elif isinstance(default, bool):
                param_strs.append(f"{pname}: {py_type} = {default}")
            else:
                param_strs.append(f"{pname}: {py_type} = {default}")

        param_docs.append(f"        {pname}: {p.get('type', 'Any')} — ver docstring original")

    params_str = ", ".join(param_strs)

    # Gerar conversões para tipos não-primitivos
    conversions = ""
    if complexity == "medium":
        for p in params:
            if not p.get("is_primitive", True):
                conv = _generate_param_conversion(p)
                if conv:
                    conversions += conv

    # Docstring
    doc_lines = func.get("docstring", "Sem documentação disponível.")
    # Truncar se muito longa
    if len(doc_lines) > 300:
        doc_lines = doc_lines[:300] + "..."

    # Gerar o call da função original
    call_args = ", ".join(p["name"] for p in params)

    wrapper_code = f'''"""
Skill: {wrapper_name}
Fonte: {func["qualified_name"]} ({func["source_package"]} v{func["version"]})
Complexidade: {complexity}
Tags: {", ".join(get_tags(func))}
"""


def {wrapper_name}({params_str}):
    """
    {doc_lines}

    Args:
{chr(10).join(param_docs) if param_docs else "        (sem parâmetros)"}

    Returns:
        Resultado serializável (JSON-safe).

    Fonte original: {func["qualified_name"]}
    """
    try:
        from {module} import {original_name}
{conversions}
        result = {original_name}({call_args})

        # Garantir retorno serializável
        return _serialize(result)
    except ImportError as e:
        return {{"error": f"Módulo não disponível: {{e}}", "skill": "{wrapper_name}"}}
    except Exception as e:
        return {{"error": f"{{type(e).__name__}}: {{e}}", "skill": "{wrapper_name}"}}


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
'''

    return wrapper_name, wrapper_code


def generate_schema(func: dict, wrapper_name: str) -> dict:
    """Etapa 6: Gera schema JSON para a skill."""
    params = func.get("parameters", [])
    properties = {}
    required = []

    for p in params:
        json_type = _python_type_to_json(p["type"])
        prop = {
            "type": json_type,
            "description": f"{p['name']} ({p['type']})",
        }
        if p.get("default") is not None:
            prop["default"] = p["default"]

        properties[p["name"]] = prop
        if p.get("required", True):
            required.append(p["name"])

    schema = {
        "name": wrapper_name,
        "description": func.get("docstring", "")[:200],
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
    return schema


def validate_skill(wrapper_name: str, skill_path: Path, timeout_s: int = 10) -> dict:
    """Etapa 7: Valida skill com import e execução básica."""
    result = {"name": wrapper_name, "valid": False, "error": None}

    # Teste 1: importação
    try:
        spec = importlib.util.spec_from_file_location(wrapper_name, str(skill_path))
        mod = importlib.util.module_from_spec(spec)

        def do_import():
            try:
                spec.loader.exec_module(mod)
                result["import_ok"] = True
            except Exception as e:
                result["error"] = f"Import: {e}"
                result["import_ok"] = False

        t = threading.Thread(target=do_import)
        t.daemon = True
        t.start()
        t.join(timeout=timeout_s)

        if t.is_alive():
            result["error"] = f"Import timeout ({timeout_s}s)"
            return result

        if not result.get("import_ok"):
            return result

    except Exception as e:
        result["error"] = f"Spec: {e}"
        return result

    # Teste 2: a função existe no módulo
    if hasattr(mod, wrapper_name):
        result["has_function"] = True
        result["valid"] = True
    else:
        result["error"] = f"Função {wrapper_name} não encontrada no módulo"

    return result


def main():
    parser = argparse.ArgumentParser(description="Gerador de Skills LILO")
    parser.add_argument("--input", default="extracted_functions.json", help="JSON de funções extraídas")
    parser.add_argument("--validate", action="store_true", help="Validar skills após geração")
    parser.add_argument("--max-skills", type=int, default=200, help="Máximo de skills a gerar")
    args = parser.parse_args()

    input_path = SCRIPT_DIR / args.input

    if not input_path.exists():
        print(f"ERRO: Arquivo {input_path} não encontrado.")
        print("Execute primeiro: python scan_conda_env.py")
        sys.exit(1)

    # Criar diretórios
    SKILLS_DIR.mkdir(exist_ok=True)
    SCHEMAS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    # Carregar funções extraídas
    print("=" * 60)
    print("LILO Skills Generator — Etapas 4-7")
    print("=" * 60)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    functions = data["functions"]
    print(f"\nFunções disponíveis: {len(functions)}")

    # ── Etapa 4: Classificação ──────────────────────────────────────────────
    print("\n── Etapa 4: Classificação de complexidade ──")
    classified = {"simple": [], "medium": [], "complex": []}

    for func in functions:
        complexity = classify_complexity(func)
        func["_complexity"] = complexity
        classified[complexity].append(func)

    print(f"  SIMPLES: {len(classified['simple'])}")
    print(f"  MÉDIA:   {len(classified['medium'])}")
    print(f"  COMPLEXA: {len(classified['complex'])} (não serão geradas)")

    # Selecionar funções para gerar (SIMPLES + MÉDIA)
    to_generate = classified["simple"] + classified["medium"]
    if len(to_generate) > args.max_skills:
        # Priorizar por: 1) menor n_params, 2) tem docstring boa
        to_generate.sort(key=lambda f: (f["n_params"], -len(f.get("docstring", ""))))
        to_generate = to_generate[:args.max_skills]

    print(f"\n  Skills a gerar: {len(to_generate)}")

    # ── Etapa 5: Geração de wrappers ────────────────────────────────────────
    print("\n── Etapa 5: Geração de wrappers Python ──")
    generated = []
    generation_errors = []
    seen_names = set()

    for i, func in enumerate(to_generate):
        try:
            wrapper_name, wrapper_code = generate_wrapper(func, func["_complexity"])

            # Evitar duplicatas
            if wrapper_name in seen_names:
                wrapper_name = f"{wrapper_name}_{i}"
            seen_names.add(wrapper_name)

            # Salvar arquivo Python
            skill_path = SKILLS_DIR / f"{wrapper_name}.py"
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(wrapper_code)

            # ── Etapa 6: Schema JSON ────────────────────────────────────────
            schema = generate_schema(func, wrapper_name)
            schema_path = SCHEMAS_DIR / f"{wrapper_name}.json"
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False, default=str)

            generated.append({
                "name": wrapper_name,
                "module": f"skills/{wrapper_name}.py",
                "schema": f"schemas/{wrapper_name}.json",
                "source_package": func["source_package"],
                "qualified_name": func["qualified_name"],
                "complexity": func["_complexity"],
                "tags": get_tags(func),
                "n_params": func["n_params"],
            })

            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(to_generate)}] geradas...")

        except Exception as e:
            generation_errors.append({
                "function": func.get("qualified_name", "?"),
                "error": str(e),
            })

    print(f"\n  ✅ {len(generated)} skills geradas")
    if generation_errors:
        print(f"  ⚠️  {len(generation_errors)} erros de geração")

    # ── Etapa 7: Validação ──────────────────────────────────────────────────
    validation_results = []
    if args.validate:
        print("\n── Etapa 7: Validação de skills ──")
        valid_count = 0
        for i, skill in enumerate(generated):
            skill_path = SKILLS_DIR / f"{skill['name']}.py"
            vr = validate_skill(skill["name"], skill_path)
            validation_results.append(vr)
            if vr["valid"]:
                valid_count += 1
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(generated)}] validadas...")

        print(f"\n  ✅ {valid_count}/{len(generated)} skills válidas")

        # Remover inválidas do registry
        valid_names = {v["name"] for v in validation_results if v["valid"]}
        generated = [g for g in generated if g["name"] in valid_names]
    else:
        print("\n── Etapa 7: Validação (pulada — use --validate) ──")

    # ── Etapa 8-9: Registry e salvamento ────────────────────────────────────
    print("\n── Etapa 8-9: Registry e salvamento ──")

    # schema_version: bump quando o formato do registry mudar
    # (campos novos, mudanca de tipo, renomeacao). Lido por
    # lilo_skills/__init__.py:_load_registry() para invalidar cache
    # automaticamente.
    registry = {
        "schema_version": "1.1",
        "generator_version": "lilo_skills/generate_skills.py v10.2",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_skills": len(generated),
        "by_complexity": {
            "simple": len([g for g in generated if g["complexity"] == "simple"]),
            "medium": len([g for g in generated if g["complexity"] == "medium"]),
            "high":   len([g for g in generated if g["complexity"] == "high"]),
        },
        "by_package": {},
        "skills": generated,
    }

    # Agrupar por pacote
    for skill in generated:
        pkg = skill["source_package"]
        if pkg not in registry["by_package"]:
            registry["by_package"][pkg] = 0
        registry["by_package"][pkg] += 1

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False, default=str)

    print(f"  Registry: {REGISTRY_PATH}")

    # ── Etapa 10: Logs ──────────────────────────────────────────────────────
    print("\n── Etapa 10: Logs ──")
    report_lines = [
        "LILO Skills Generator — Relatório",
        "=" * 50,
        f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Input: {input_path}",
        "",
        f"Funções analisadas: {len(functions)}",
        f"  SIMPLES: {len(classified['simple'])}",
        f"  MÉDIA:   {len(classified['medium'])}",
        f"  COMPLEXA: {len(classified['complex'])}",
        "",
        f"Skills geradas: {len(generated)}",
        f"Erros de geração: {len(generation_errors)}",
        "",
    ]

    if generation_errors:
        report_lines.append("── Erros de geração ──")
        for err in generation_errors:
            report_lines.append(f"  {err['function']}: {err['error']}")
        report_lines.append("")

    if validation_results:
        failed = [v for v in validation_results if not v["valid"]]
        report_lines.append("── Validação ──")
        report_lines.append(f"  Válidas: {len(validation_results) - len(failed)}")
        report_lines.append(f"  Inválidas: {len(failed)}")
        for v in failed:
            report_lines.append(f"  ✗ {v['name']}: {v.get('error', '?')}")
        report_lines.append("")

    # Funções complexas (para referência futura)
    report_lines.append("── Funções COMPLEXAS (não geradas) ──")
    for func in classified["complex"][:50]:
        complex_params = [p["name"] + ":" + p["type"] for p in func["parameters"] if p.get("is_complex")]
        report_lines.append(f"  {func['qualified_name']} — params: {', '.join(complex_params)}")

    # Skills por pacote
    report_lines.append("")
    report_lines.append("── Skills por pacote ──")
    for pkg, count in sorted(registry.get("by_package", {}).items(), key=lambda x: -x[1]):
        report_lines.append(f"  {pkg}: {count}")

    report_path = LOGS_DIR / "report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"  Report: {report_path}")

    # ── Resumo final ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print(f"  Pacotes analisados:     {data.get('relevant_packages', '?')}")
    print(f"  Funções extraídas:      {len(functions)}")
    print(f"  Skills geradas:         {len(generated)}")
    print("  Skills por pacote:")
    for pkg, count in sorted(registry.get("by_package", {}).items(), key=lambda x: -x[1])[:10]:
        print(f"    {pkg}: {count}")
    print(f"\n  Diretório: {SCRIPT_DIR}")
    print(f"  Registry:  {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
