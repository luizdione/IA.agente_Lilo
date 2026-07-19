#!/usr/bin/env python3
"""
scan_conda_env.py — Scanner offline de ambiente Conda para LILO Skills
======================================================================
Etapas 1-3 do pipeline de geração de skills.
Roda 100% offline, sem tokens LLM.

Uso:
    python scan_conda_env.py
    python scan_conda_env.py --conda-prefix C:\\Users\\luizd\\miniforge3
    python scan_conda_env.py --output extracted_functions.json

Saída: JSON com funções extraídas, pronto para a Etapa 4 (classificação).
"""

import json
import sys
import inspect
import importlib
import pkgutil
import subprocess
import time
from pathlib import Path
from contextlib import contextmanager
import argparse

# ── Timeout cross-platform ──────────────────────────────────────────────────

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds):
    """Timeout context manager (Windows-compatible via threading)."""
    import threading
    result = [None]
    error = [None]
    completed = threading.Event()

    def wrapper(func, *args, **kwargs):
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            error[0] = e
        finally:
            completed.set()

    # Yield control — caller uses it differently
    # For simplicity, we use a simpler approach: just track time
    start = time.time()
    yield
    elapsed = time.time() - start
    if elapsed > seconds:
        raise TimeoutError(f"Operação excedeu {seconds}s (levou {elapsed:.1f}s)")


# ── Configuração ────────────────────────────────────────────────────────────

# Palavras-chave para filtrar pacotes relevantes (bioinformática, estatística, data science)
RELEVANT_KEYWORDS = [
    "bio", "seq", "gen", "protein", "stat", "math", "data", "align",
    "phylo", "chem", "mol", "blast", "fasta", "fastq", "vcf", "bam",
    "sam", "gff", "bed", "pdb", "dna", "rna", "amino", "codon",
    "enzyme", "kinase", "genom", "proteom", "transcriptom", "metabol",
    "scipy", "numpy", "pandas", "sklearn", "scikit", "statsmodels",
    "seaborn", "matplotlib", "plotly", "networkx", "igraph",
    "ete3", "dendro", "clustal", "muscle", "hmm", "markov",
    "pysam", "pyvcf", "pybedtools", "biopython", "biotite",
    "mdanalysis", "rdkit", "openbabel", "prody", "modeller",
    "scanpy", "anndata", "loompy", "scvi", "cellrank",
    "pydeseq2", "diffxpy", "gseapy", "goatools",
    "lifelines", "kaplan", "survival",
    "pingouin", "researchpy", "factor_analyzer",
    "xgboost", "lightgbm", "catboost", "optuna", "hyperopt",
    "dask", "polars", "vaex", "modin",
    "tabulate", "openpyxl", "xlsxwriter",
]

# Pacotes a ignorar (sistema, UI, internos)
EXCLUDE_PACKAGES = {
    "pip", "setuptools", "wheel", "pkg_resources", "distutils",
    "tkinter", "turtle", "idlelib", "turtledemo",
    "test", "tests", "unittest", "_pytest", "pytest",
    "sphinx", "docutils", "pygments",
    "IPython", "ipykernel", "ipywidgets", "jupyter",
    "conda", "conda_build", "conda_env",
    "win32com", "win32api", "pythoncom", "pywintypes",
    "certifi", "charset_normalizer", "urllib3",
    "ensurepip", "venv", "lib2to3", "antigravity",
    "__pycache__", "_distutils_hack",
}

# Tipos primitivos aceitos como parâmetros
PRIMITIVE_TYPES = {
    "str", "int", "float", "bool", "list", "dict", "tuple",
    "List", "Dict", "Tuple", "Optional", "Union",
    "None", "NoneType", "Any",
    "string", "integer", "number", "boolean", "array", "object",
}

# Tipos complexos que indicam funções difíceis de wrapper
COMPLEX_TYPE_INDICATORS = [
    "DataFrame", "Series", "ndarray", "Array", "Tensor",
    "SeqRecord", "Seq", "Alignment", "MultipleSeqAlignment",
    "AnnData", "ScanpyData",
    "Figure", "Axes", "Plot",
    "Model", "Estimator", "Pipeline",
    "File", "IO", "Stream", "Buffer",
    "Connection", "Session", "Engine",
    "Tree", "Phylo", "Clade",
]


def discover_packages_conda(conda_prefix: str = "") -> list[dict]:
    """Etapa 1: Descobre pacotes via conda list --json."""
    packages = []

    # Tentar conda list
    try:
        cmd = ["conda", "list", "--json"]
        if conda_prefix:
            cmd.extend(["--prefix", conda_prefix])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            conda_pkgs = json.loads(result.stdout)
            for pkg in conda_pkgs:
                packages.append({
                    "name": pkg.get("name", ""),
                    "version": pkg.get("version", ""),
                    "channel": pkg.get("channel", ""),
                    "source": "conda",
                })
            print(f"[CONDA] {len(packages)} pacotes encontrados via conda list")
            return packages
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] conda list falhou: {e}")

    # Fallback: pip list
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            pip_pkgs = json.loads(result.stdout)
            for pkg in pip_pkgs:
                packages.append({
                    "name": pkg.get("name", ""),
                    "version": pkg.get("version", ""),
                    "channel": "pip",
                    "source": "pip",
                })
            print(f"[PIP] {len(packages)} pacotes encontrados via pip list")
            return packages
    except Exception as e:
        print(f"[WARN] pip list falhou: {e}")

    # Fallback final: pkgutil
    for importer, name, ispkg in pkgutil.iter_modules():
        packages.append({
            "name": name, "version": "unknown",
            "channel": "local", "source": "pkgutil",
        })
    print(f"[PKGUTIL] {len(packages)} módulos encontrados via pkgutil")
    return packages


def filter_relevant(packages: list[dict]) -> list[dict]:
    """Etapa 2: Filtra pacotes cientificamente relevantes."""
    relevant = []
    excluded = []

    for pkg in packages:
        name = pkg["name"].lower().replace("-", "_")

        # Excluir pacotes de sistema
        if name in EXCLUDE_PACKAGES or name.startswith("_"):
            excluded.append((pkg["name"], "sistema/interno"))
            continue

        # Verificar keywords
        is_relevant = False
        for kw in RELEVANT_KEYWORDS:
            if kw in name:
                is_relevant = True
                break

        if is_relevant:
            relevant.append(pkg)
        else:
            excluded.append((pkg["name"], "sem keyword relevante"))

    print(f"[FILTER] {len(relevant)} relevantes / {len(excluded)} excluídos")
    return relevant, excluded


def _get_type_name(annotation) -> str:
    """Extrai nome legível de uma anotação de tipo."""
    if annotation is inspect.Parameter.empty:
        return "Any"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    if hasattr(annotation, "__origin__"):
        # typing generics (List[str], Optional[int], etc.)
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            arg_names = ", ".join(_get_type_name(a) for a in args)
            return f"{origin_name}[{arg_names}]"
        return origin_name
    return str(annotation).replace("typing.", "")


def _is_primitive_type(type_name: str) -> bool:
    """Verifica se o tipo é primitivo/serializável."""
    # Limpar generics
    base = type_name.split("[")[0].strip()
    return base in PRIMITIVE_TYPES


def _is_complex_type(type_name: str) -> bool:
    """Verifica se o tipo indica complexidade."""
    for indicator in COMPLEX_TYPE_INDICATORS:
        if indicator.lower() in type_name.lower():
            return True
    return False


def _safe_import(module_name: str, timeout_s: int = 10):
    """Importa módulo com timeout e tratamento de erro."""
    import threading

    result = {"module": None, "error": None}

    def do_import():
        try:
            result["module"] = importlib.import_module(module_name)
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=do_import)
    t.daemon = True
    t.start()
    t.join(timeout=timeout_s)

    if t.is_alive():
        return None, f"Timeout ({timeout_s}s) ao importar {module_name}"
    if result["error"]:
        return None, result["error"]
    return result["module"], None


def extract_functions(packages: list[dict], max_per_package: int = 50) -> tuple:
    """
    Etapa 3: Extrai funções de cada pacote via introspecção.

    Returns:
        (functions_list, import_errors)
    """
    all_functions = []
    import_errors = []

    for i, pkg in enumerate(packages):
        pkg_name = pkg["name"].replace("-", "_")
        print(f"  [{i+1}/{len(packages)}] Escaneando {pkg_name}...", end=" ", flush=True)

        # Importar módulo principal
        mod, err = _safe_import(pkg_name)
        if err:
            # Tentar variações comuns
            alternatives = [
                pkg_name.lower(),
                pkg_name.replace("python_", "").replace("py", ""),
            ]
            # Mapeamento manual de nomes conhecidos
            IMPORT_MAP = {
                "biopython": "Bio",
                "scikit_learn": "sklearn",
                "scikit_bio": "skbio",
                "pillow": "PIL",
                "pyyaml": "yaml",
                "python_dateutil": "dateutil",
                "beautifulsoup4": "bs4",
                "opencv_python": "cv2",
                "tables": "tables",
                "h5py": "h5py",
            }
            if pkg_name in IMPORT_MAP:
                alternatives.insert(0, IMPORT_MAP[pkg_name])

            imported = False
            for alt in alternatives:
                if alt == pkg_name:
                    continue
                mod, err2 = _safe_import(alt)
                if mod:
                    pkg_name = alt  # usar o nome que funcionou
                    imported = True
                    break

            if not imported:
                import_errors.append({
                    "package": pkg["name"],
                    "error": err,
                    "tried": [pkg_name] + alternatives,
                })
                print("FALHOU")
                continue

        # Extrair funções do módulo
        count = 0
        try:
            members = inspect.getmembers(mod)
        except Exception as e:
            import_errors.append({"package": pkg["name"], "error": f"getmembers falhou: {e}"})
            print("ERRO inspect")
            continue

        for name, obj in members:
            if count >= max_per_package:
                break

            # Filtrar: só funções públicas com docstring
            if name.startswith("_"):
                continue
            if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
                continue

            docstring = inspect.getdoc(obj) or ""
            if not docstring or len(docstring) < 10:
                continue

            # Extrair parâmetros
            params = []
            try:
                sig = inspect.signature(obj)
                for pname, param in sig.parameters.items():
                    if pname in ("self", "cls"):
                        continue
                    type_name = _get_type_name(param.annotation)
                    has_default = param.default is not inspect.Parameter.empty
                    default_val = None
                    if has_default:
                        try:
                            json.dumps(param.default)  # é serializável?
                            default_val = param.default
                        except (TypeError, ValueError):
                            default_val = str(param.default)

                    params.append({
                        "name": pname,
                        "type": type_name,
                        "required": not has_default,
                        "default": default_val,
                        "is_primitive": _is_primitive_type(type_name),
                        "is_complex": _is_complex_type(type_name),
                    })
            except (ValueError, TypeError):
                # Funções builtins sem signature
                params = [{"name": "args", "type": "Any", "required": True,
                           "is_primitive": True, "is_complex": False}]

            # Extrair tipo de retorno
            return_type = "Any"
            try:
                sig = inspect.signature(obj)
                if sig.return_annotation is not inspect.Parameter.empty:
                    return_type = _get_type_name(sig.return_annotation)
            except (ValueError, TypeError):
                pass

            func_info = {
                "name": name,
                "qualified_name": f"{pkg_name}.{name}",
                "module": pkg_name,
                "source_package": pkg["name"],
                "version": pkg["version"],
                "docstring": docstring[:500],  # truncar docs longos
                "parameters": params,
                "return_type": return_type,
                "n_params": len(params),
                "has_complex_params": any(p["is_complex"] for p in params),
                "all_primitive_params": all(p["is_primitive"] for p in params),
            }
            all_functions.append(func_info)
            count += 1

        # Também escanear submódulos conhecidos (1 nível)
        submodules_to_scan = []
        try:
            pkg_path = getattr(mod, "__path__", None)
            if pkg_path:
                for importer, subname, ispkg in pkgutil.iter_modules(pkg_path):
                    if not subname.startswith("_") and not subname in ("test", "tests", "testing"):
                        submodules_to_scan.append(f"{pkg_name}.{subname}")
        except Exception:
            pass

        for submod_name in submodules_to_scan[:10]:  # max 10 submódulos
            if count >= max_per_package:
                break
            submod, err = _safe_import(submod_name, timeout_s=5)
            if not submod:
                continue
            try:
                for name, obj in inspect.getmembers(submod):
                    if count >= max_per_package:
                        break
                    if name.startswith("_") or not (inspect.isfunction(obj)):
                        continue
                    docstring = inspect.getdoc(obj) or ""
                    if not docstring or len(docstring) < 10:
                        continue

                    params = []
                    try:
                        sig = inspect.signature(obj)
                        for pname, param in sig.parameters.items():
                            if pname in ("self", "cls"):
                                continue
                            type_name = _get_type_name(param.annotation)
                            has_default = param.default is not inspect.Parameter.empty
                            default_val = None
                            if has_default:
                                try:
                                    json.dumps(param.default)
                                    default_val = param.default
                                except (TypeError, ValueError):
                                    default_val = str(param.default)
                            params.append({
                                "name": pname,
                                "type": type_name,
                                "required": not has_default,
                                "default": default_val,
                                "is_primitive": _is_primitive_type(type_name),
                                "is_complex": _is_complex_type(type_name),
                            })
                    except (ValueError, TypeError):
                        params = [{"name": "args", "type": "Any", "required": True,
                                   "is_primitive": True, "is_complex": False}]

                    return_type = "Any"
                    try:
                        sig = inspect.signature(obj)
                        if sig.return_annotation is not inspect.Parameter.empty:
                            return_type = _get_type_name(sig.return_annotation)
                    except (ValueError, TypeError):
                        pass

                    func_info = {
                        "name": name,
                        "qualified_name": f"{submod_name}.{name}",
                        "module": submod_name,
                        "source_package": pkg["name"],
                        "version": pkg["version"],
                        "docstring": docstring[:500],
                        "parameters": params,
                        "return_type": return_type,
                        "n_params": len(params),
                        "has_complex_params": any(p["is_complex"] for p in params),
                        "all_primitive_params": all(p["is_primitive"] for p in params),
                    }
                    all_functions.append(func_info)
                    count += 1
            except Exception:
                continue

        print(f"{count} funções")

    return all_functions, import_errors


def main():
    parser = argparse.ArgumentParser(description="Scanner offline de ambiente Conda para LILO Skills")
    parser.add_argument("--conda-prefix", default="", help="Caminho do ambiente Conda (ex: C:\\Users\\luizd\\miniforge3)")
    parser.add_argument("--output", default="extracted_functions.json", help="Arquivo de saída JSON")
    parser.add_argument("--max-per-package", type=int, default=50, help="Máximo de funções por pacote")
    args = parser.parse_args()

    output_dir = Path(__file__).parent
    output_path = output_dir / args.output

    print("=" * 60)
    print("LILO Skills Scanner — Etapas 1-3 (offline)")
    print("=" * 60)

    # Etapa 1: Descoberta
    print("\n── Etapa 1: Descoberta de pacotes ──")
    packages = discover_packages_conda(args.conda_prefix)
    print(f"Total: {len(packages)} pacotes")

    # Etapa 2: Filtragem
    print("\n── Etapa 2: Filtragem de pacotes relevantes ──")
    relevant, excluded = filter_relevant(packages)
    print(f"Relevantes: {len(relevant)}")

    # Etapa 3: Extração
    print("\n── Etapa 3: Extração de funções ──")
    functions, import_errors = extract_functions(relevant, max_per_package=args.max_per_package)
    print(f"\nTotal de funções extraídas: {len(functions)}")
    print(f"Erros de importação: {len(import_errors)}")

    # Classificação prévia
    simple = [f for f in functions if f["all_primitive_params"] and not f["has_complex_params"]]
    medium = [f for f in functions if not f["all_primitive_params"] and not f["has_complex_params"]]
    complex_fns = [f for f in functions if f["has_complex_params"]]

    print(f"\nClassificação prévia:")
    print(f"  SIMPLES (todos params primitivos): {len(simple)}")
    print(f"  MÉDIA (params não-primitivos mas sem complexos): {len(medium)}")
    print(f"  COMPLEXA (requer objetos específicos): {len(complex_fns)}")

    # Salvar resultado
    result = {
        "scan_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version,
        "conda_prefix": args.conda_prefix or "default",
        "total_packages": len(packages),
        "relevant_packages": len(relevant),
        "total_functions": len(functions),
        "classification": {
            "simple": len(simple),
            "medium": len(medium),
            "complex": len(complex_fns),
        },
        "packages_scanned": [p["name"] for p in relevant],
        "functions": functions,
        "import_errors": import_errors,
        "excluded_packages": excluded[:100],  # só os primeiros 100
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ Resultado salvo em: {output_path}")
    print(f"   Tamanho: {output_path.stat().st_size / 1024:.1f} KB")
    print("\nPróximo passo: execute a Etapa 4 no Cowork para gerar skills.")


if __name__ == "__main__":
    main()
