"""generate_skill_md.py -- gera SKILL.md por pacote em lilo_skills/skills/

Le `lilo_skills/registry.json` (gerado por scan_conda_env.py) e produz:

  lilo_skills/skills/<pacote>/SKILL.md

Formato Anthropic-skill com front-matter YAML:

    ---
    name: <pacote>
    description: <descricao curta>
    triggers: [...]
    ---

    # <pacote>

    Funcoes expostas via lilo_skills:
      - func_a(args) -> descricao
      - func_b(args) -> descricao
      ...

A geracao e idempotente: rodar de novo sobrescreve apenas se o conteudo
mudou. Util para CI / pipeline.

Uso:
    python lilo_skills/generate_skill_md.py
    python lilo_skills/generate_skill_md.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "registry.json"
SKILLS_DIR = HERE / "skills"


# Tags semanticas comuns -> triggers de descoberta para Claude/ClaudeCode
PACKAGE_DESCRIPTIONS: dict[str, dict] = {
    "matplotlib": {
        "description": "Visualizacao 2D: plot, hist, scatter, barras, layouts e configuracao do backend.",
        "triggers": ["plot", "grafico", "chart", "matplotlib", "figura", "subplot"],
    },
    "numpy": {
        "description": "Array numerico N-D, algebra linear, FFT, RNG e operacoes vetorizadas.",
        "triggers": ["array", "numpy", "matriz", "vetor", "fft", "linalg"],
    },
    "scipy": {
        "description": "Estatistica, otimizacao, interpolacao, ODEs e processamento de sinal.",
        "triggers": ["scipy", "estatistica", "otimizacao", "interpolar", "anova", "t-test"],
    },
    "pandas": {
        "description": "DataFrames, leitura/escrita CSV/Excel/SQL e analise tabular.",
        "triggers": ["pandas", "dataframe", "csv", "tabela", "groupby", "merge"],
    },
    "seaborn": {
        "description": "Visualizacao estatistica de alto-nivel sobre matplotlib.",
        "triggers": ["seaborn", "heatmap", "violinplot", "pairplot", "regplot"],
    },
    "mpmath": {
        "description": "Aritmetica de precisao arbitraria (real e complexa).",
        "triggers": ["mpmath", "precisao arbitraria", "high precision"],
    },
    "openpyxl": {
        "description": "Leitura/escrita de planilhas Excel .xlsx sem dependencia de MS Office.",
        "triggers": ["excel", "xlsx", "planilha", "openpyxl"],
    },
    "xlsxwriter": {
        "description": "Criacao de planilhas .xlsx com formatacao, formulas e graficos.",
        "triggers": ["xlsxwriter", "excel", "planilha", "xlsx"],
    },
    "tornado": {
        "description": "Servidor HTTP assincrono, websockets e utilitarios IO.",
        "triggers": ["tornado", "http", "websocket", "async", "ioloop"],
    },
    "jsonschema": {
        "description": "Validacao de objetos JSON contra esquema JSON Schema.",
        "triggers": ["jsonschema", "validar json", "json schema"],
    },
    "importlib-metadata": {
        "description": "Introspeccao de metadados de pacotes instalados.",
        "triggers": ["importlib", "metadata", "package", "dist-info"],
    },
    "tabulate": {
        "description": "Renderizacao de tabelas em texto/Markdown a partir de listas.",
        "triggers": ["tabulate", "tabela texto", "markdown table"],
    },
    "idna": {
        "description": "Codificacao IDNA de dominios internacionais.",
        "triggers": ["idna", "punycode", "dominio internacional"],
    },
}


def _slugify(name: str) -> str:
    return name.replace(".", "_").replace("/", "_").strip()


def _front_matter(pkg: str, n: int) -> str:
    meta = PACKAGE_DESCRIPTIONS.get(pkg, {})
    desc = meta.get(
        "description",
        f"Skills auto-geradas a partir de funcoes de {pkg} ({n} funcoes).",
    )
    triggers = meta.get("triggers", [pkg])
    triggers_yaml = "[" + ", ".join(repr(t) for t in triggers) + "]"
    return (
        "---\n"
        f"name: {pkg}\n"
        f"description: {desc}\n"
        f"triggers: {triggers_yaml}\n"
        f"functions: {n}\n"
        "source: lilo_skills/registry.json\n"
        "---\n"
    )


def _body(pkg: str, items: list[dict]) -> str:
    lines = [f"\n# {pkg}\n"]
    lines.append(
        f"\nFuncoes expostas via `lilo_skills` ({len(items)} no total). "
        "Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e "
        "chamada via MCP tool `lilo_run_skill` ou import direto:\n"
    )
    lines.append("\n```python")
    lines.append(f"from lilo_skills import run_skill")
    lines.append(f'res = run_skill("{items[0]["name"]}", **kwargs)')
    lines.append("```\n")
    lines.append("\n## Funcoes\n")
    for it in sorted(items, key=lambda x: x["name"]):
        params = f"{it.get('n_params', 0)} parametro(s)"
        tags = ", ".join(it.get("tags", []) or [])
        tag_str = f" [{tags}]" if tags else ""
        lines.append(
            f"- **{it['name']}** -- `{it.get('qualified_name','?')}` -- {params}{tag_str}"
        )
    lines.append("")
    return "\n".join(lines)


def generate(dry_run: bool = False) -> tuple[int, int]:
    """Gera SKILL.md por pacote. Retorna (criados, atualizados)."""
    if not REGISTRY.exists():
        print(f"ERRO: registry.json nao encontrado em {REGISTRY}", file=sys.stderr)
        return (0, 0)

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    by_pkg: dict[str, list[dict]] = defaultdict(list)
    for s in skills:
        pkg = s.get("source_package", "misc")
        by_pkg[pkg].append(s)

    created = 0
    updated = 0
    for pkg, items in sorted(by_pkg.items()):
        pkg_dir = SKILLS_DIR / _slugify(pkg)
        skill_md = pkg_dir / "SKILL.md"

        content = _front_matter(pkg, len(items)) + _body(pkg, items)

        if dry_run:
            print(f"[DRY] {skill_md}  ({len(items)} funcoes)")
            continue

        existed = skill_md.exists()
        if existed:
            try:
                old = skill_md.read_text(encoding="utf-8")
                if old == content:
                    continue
                updated += 1
            except Exception:
                updated += 1
        else:
            created += 1
            pkg_dir.mkdir(parents=True, exist_ok=True)

        skill_md.write_text(content, encoding="utf-8")
        print(f"{'UPD' if existed else 'NEW'}  {skill_md}  ({len(items)} fn)")

    return created, updated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Apenas lista o que seria gerado")
    args = ap.parse_args()
    c, u = generate(dry_run=args.dry_run)
    if not args.dry_run:
        print(f"\nResumo: {c} criados, {u} atualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
