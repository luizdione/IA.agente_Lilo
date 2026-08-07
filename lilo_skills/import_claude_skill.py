"""
lilo_skills/import_claude_skill.py
==================================
Importa skills PESSOAIS do Claude (~/.claude/skills/<slug>) para o LILO
(lilo_skills/skills/<slug>), SEM TOCAR na origem (só shutil.copy2/read).

Trilho CÓDIGO (scripts CLI de análise): copia os .py da skill e gera, POR script,
um wrapper flat `skills/<tool>.py` que RODA o script real no env conda de análise
(default 'datascience', que tem numpy/pandas/scipy/...) via
`shared.exec_env.run_script`, + `schemas/<tool>.json` (chave `parameters`) +
entrada em `registry.json`. Idempotente; `--dry-run` mostra o plano.

Assim as skills do dono passam a funcionar no LILO (CLI/dashboard/MCP) rodando
100% local, sem gastar tokens de Claude, e sem alterar as skills originais.

Uso:
    python lilo_skills/import_claude_skill.py perfil_dados
    python lilo_skills/import_claude_skill.py --all
    python lilo_skills/import_claude_skill.py <slug> --script scripts/x.py:tool_x
    python lilo_skills/import_claude_skill.py perfil_dados --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

CLAUDE_SKILLS = Path.home() / ".claude" / "skills"
LILO_SKILLS = Path(__file__).resolve().parent
SKILLS_DIR = LILO_SKILLS / "skills"
SCHEMAS_DIR = LILO_SKILLS / "schemas"
REGISTRY = LILO_SKILLS / "registry.json"

# Spec das skills de ALTA portabilidade que PODEM ir ao git (script relativo à
# skill -> nome da tool no LILO). dest = pasta destino em skills/ (default: a chave).
#
# REGRA DE IP (2026-08-06): skills de redacao/AUDITORIA de ARTIGO (build_paper,
# auditoria_paper, biblioteca_ref, git_dione, montagem_resultados, check_integrity)
# NAO entram aqui — sao IP privado, fora do git (ver .gitignore). Para importa-las
# LOCALMENTE (sem versionar), use a flag --script:
#   python import_claude_skill.py biblioteca_ref --script scripts/bibref.py:bibref
# So skills NAO-artigo ficam no PORT_SPEC versionado.
PORT_SPEC: dict[str, dict] = {
    "perfil_dados": {"src": "perfil_dados",
                     "scripts": {"scripts/perfil.py": "perfil_dados"}},
    "graphpad_prism": {"src": "graphpad_prism", "scripts": {
        "scripts/prism_extract.py": "gpp_extract",
        "scripts/prism_reanalyze.py": "gpp_reanalyze",
        "scripts/emf_convert.py": "gpp_emf"}},
}

_WRAPPER_TMPL = '''"""Skill portada de ~/.claude/skills/{src} (NAO modifica a origem).
Roda o script real no env conda de analise via shared.exec_env.run_script."""
from pathlib import Path

_SCRIPT = Path(__file__).parent / "{dest}" / "{relpath}"


def {tool}(args=None, env="datascience", timeout=300):
    """Executa {relpath} (skill {src}). args = lista OU string de argumentos CLI."""
    from shared.exec_env import run_script
    return run_script(str(_SCRIPT), args=args, env=env, timeout=timeout)
'''


def _desc_from_skill_md(src_dir: Path, tool: str) -> str:
    md = src_dir / "SKILL.md"
    desc = ""
    if md.exists():
        txt = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^description:\s*[>|]?-?\s*(.+)$", txt, re.M)
        if m:
            desc = " ".join(m.group(1).split())[:300]
    return desc or ("Skill portada '%s' (roda script local no env datascience)." % tool)


def _schema(tool: str, desc: str, relpath: str) -> dict:
    return {
        "name": tool,
        "description": desc + " [args: lista/str de CLI; env=datascience; timeout=300s]",
        "parameters": {
            "type": "object",
            "properties": {
                "args": {"type": "array", "items": {"type": "string"},
                         "description": "Argumentos CLI do script (ex.: caminho do arquivo). Pode ser string."},
                "env": {"type": "string", "default": "datascience",
                        "description": "env conda (numpy/pandas/...). Vazio = Python do LILO."},
                "timeout": {"type": "integer", "default": 300},
            },
        },
    }


def _load_registry() -> dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"skills": [], "total_skills": 0, "schema_version": "1.1"}


def import_skill(key: str, spec: dict, dry_run: bool = False) -> list[str]:
    src_slug = spec["src"]
    dest_slug = key
    src_dir = CLAUDE_SKILLS / src_slug
    if not src_dir.is_dir():
        return ["[SKIP] origem inexistente: %s" % src_dir]

    actions: list[str] = []
    dest_dir = SKILLS_DIR / dest_slug

    # 1) copiar os .py da(s) pasta(s)-fonte dos scripts (preserva helpers)
    src_dirs = {str(Path(rel).parent) for rel in spec["scripts"]}
    for reldir in sorted(src_dirs):
        s = src_dir / reldir if reldir not in (".", "") else src_dir
        d = dest_dir / reldir if reldir not in (".", "") else dest_dir
        pys = sorted(s.glob("*.py"))
        actions.append("copy %d .py: %s -> %s" % (len(pys), s, d))
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)
            for py in pys:
                shutil.copy2(py, d / py.name)
    # copiar SKILL.md (referência)
    if (src_dir / "SKILL.md").exists():
        actions.append("copy SKILL.md")
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_dir / "SKILL.md", dest_dir / "SKILL.md")

    # 2) por script: wrapper flat + schema + registry
    reg = _load_registry()
    existing = {s["name"]: i for i, s in enumerate(reg.get("skills", []))}
    for relpath, tool in spec["scripts"].items():
        desc = _desc_from_skill_md(src_dir, tool)
        wrapper = _WRAPPER_TMPL.format(src=src_slug, dest=dest_slug,
                                       relpath=relpath.replace("\\", "/"), tool=tool)
        actions.append("wrapper skills/%s.py + schema + registry (%s)" % (tool, relpath))
        if not dry_run:
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
            (SKILLS_DIR / (tool + ".py")).write_text(wrapper, encoding="utf-8")
            (SCHEMAS_DIR / (tool + ".json")).write_text(
                json.dumps(_schema(tool, desc, relpath), ensure_ascii=False, indent=2),
                encoding="utf-8")
            item = {"name": tool, "module": "", "schema": tool + ".json",
                    "source_package": "claude_skill:" + src_slug,
                    "qualified_name": tool, "complexity": "med",
                    "tags": ["ported", src_slug], "n_params": 3}
            if tool in existing:
                reg["skills"][existing[tool]] = item
            else:
                reg["skills"].append(item)
    if not dry_run:
        reg["total_skills"] = len(reg["skills"])
        REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return actions


def main():
    ap = argparse.ArgumentParser(description="Importa skill do Claude para o LILO (sem tocar na origem).")
    ap.add_argument("slug", nargs="?", help="slug da skill (ou omita com --all)")
    ap.add_argument("--all", action="store_true", help="importa as skills NAO-artigo do PORT_SPEC")
    ap.add_argument("--script", action="append", default=[],
                    help="relpath.py:tool (para skills fora do PORT_SPEC)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    todo: dict[str, dict] = {}
    if args.all:
        todo = dict(PORT_SPEC)
    elif args.slug and args.script:
        todo = {args.slug: {"src": args.slug,
                            "scripts": dict(s.split(":", 1) for s in args.script)}}
    elif args.slug in PORT_SPEC:
        todo = {args.slug: PORT_SPEC[args.slug]}
    elif args.slug:
        print("[ERRO] '%s' nao esta no PORT_SPEC; use --script relpath.py:tool" % args.slug)
        sys.exit(2)
    else:
        ap.print_help()
        sys.exit(1)

    for key, spec in todo.items():
        print("=== %s%s ===" % (key, " (dry-run)" if args.dry_run else ""))
        for a in import_skill(key, spec, dry_run=args.dry_run):
            print("  " + a)
    if not args.dry_run:
        print("\nOK. Reinicie o cliente MCP (a lista de tools e cacheada por sessao).")


if __name__ == "__main__":
    main()
