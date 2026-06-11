"""
scripts/mover_obsoletos.py
==========================
Move arquivos identificados como OBSOLETOS para `obsoletos/<caminho_original>/`,
preservando a estrutura de diretorios. Gera `obsoletos/manifest.json` com
timestamps, SHA256 e mapeamento origem -> destino para reverter depois.

NAO DELETA NADA. So move (shutil.move). Se algo der errado:
    python scripts/reverter_obsoletos.py --all

Uso:
    python scripts/mover_obsoletos.py --dry-run    # simula, nao mexe em nada
    python scripts/mover_obsoletos.py --apply      # move de verdade

Categorias movidas:
  - subarvore agents/PDFs_library/app/ (implementacao antiga)
  - PDFs_library/launcher.py, run.py, docker/, models/
  - agents/scholaragent: app.py, ollama_client.py, pdf_processor.py,
    reference_formatter.py, templates/, uploads/
  - agents/Analise_SQL: sql_analyzer_gui.py, sql_statistical_analyzer.py
  - logs/litellm_old/, lilo_skills/logs/
  - LIMPAR_LIXO.bat, arch-v10.bat (raiz)
  - todos os __pycache__/ (regenerados)

Para curar lilo_skills/skills/ rode `scripts/curar_skills.py` separado.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "obsoletos"
MANIFEST = DEST / "manifest.json"


# ============================================================================
# CONFIG -- listas de arquivos/diretorios a mover (relativos a ROOT)
# ============================================================================

OBSOLETE_FILES = [
    # --- agents/scholaragent: implementacao Flask antiga ---
    "agents/scholaragent/app.py",
    "agents/scholaragent/ollama_client.py",
    "agents/scholaragent/pdf_processor.py",
    "agents/scholaragent/reference_formatter.py",

    # --- agents/Analise_SQL ---
    "agents/Analise_SQL/sql_analyzer_gui.py",
    "agents/Analise_SQL/sql_statistical_analyzer.py",

    # --- agents/PDFs_library: implementacao antiga ---
    "agents/PDFs_library/launcher.py",
    "agents/PDFs_library/run.py",

    # --- raiz: scripts antigos ---
    "LIMPAR_LIXO.bat",
    "arch-v10.bat",
]

OBSOLETE_DIRS = [
    # --- subarvore antiga inteira ---
    "agents/PDFs_library/app",
    "agents/PDFs_library/docker",
    "agents/PDFs_library/models",
    "agents/scholaragent/templates",
    "agents/scholaragent/uploads",

    # --- logs vazios/antigos ---
    "logs/litellm_old",
    "lilo_skills/logs",
]

# __pycache__ sao tratados separadamente (sao regenerados, nao precisam manifest)
PYCACHE_GLOB = "**/__pycache__"


# ============================================================================
# Utilities
# ============================================================================

def sha256_of(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def collect_targets():
    """Retorna lista de tuplas (origem_abs, destino_abs, kind, sha256)."""
    items = []
    for rel in OBSOLETE_FILES:
        src = ROOT / rel
        if src.exists() and src.is_file():
            dst = DEST / rel
            items.append((src, dst, "file", sha256_of(src)))
    for rel in OBSOLETE_DIRS:
        src = ROOT / rel
        if src.exists() and src.is_dir():
            dst = DEST / rel
            items.append((src, dst, "dir", ""))
    return items


def collect_pycaches():
    """Retorna __pycache__ fora de obsoletos/ e _ARCHIVE_v10/."""
    items = []
    for p in ROOT.glob(PYCACHE_GLOB):
        if not p.is_dir():
            continue
        rp = relpath(p)
        if rp.startswith("obsoletos/") or rp.startswith("_ARCHIVE_v10/"):
            continue
        items.append((p, DEST / rp, "pycache", ""))
    return items


# ============================================================================
# Actions
# ============================================================================

def do_dry_run(targets, pycaches):
    print("=== DRY RUN -- nada sera movido ===\n")
    print(f"Destino base: {DEST}\n")
    print(f"OBSOLETOS ({len(targets)}):")
    for src, dst, kind, sha in targets:
        size = src.stat().st_size if src.is_file() else (
            sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) if src.is_dir() else 0
        )
        print(f"  [{kind:5s}] {relpath(src):<60s} -> obsoletos/{relpath(src)}  ({size:,} bytes)")
    print(f"\nPYCACHE ({len(pycaches)}):")
    for src, dst, kind, sha in pycaches:
        print(f"  [{kind:5s}] {relpath(src)}")
    total_size = sum(
        s.stat().st_size if s.is_file()
        else sum(f.stat().st_size for f in s.rglob("*") if f.is_file())
        for s, _, k, _ in targets
    )
    print(f"\nTotal a mover (sem __pycache__): {total_size:,} bytes ({total_size/1024:.1f} KB)")


def do_apply(targets, pycaches):
    DEST.mkdir(exist_ok=True)
    moved = []
    skipped = []
    timestamp = datetime.now().isoformat()

    print(f"=== APLICANDO -- destino: {DEST} ===\n")

    # 1. arquivos e diretorios obsoletos (com manifest)
    for src, dst, kind, sha in targets:
        if not src.exists():
            skipped.append({"src": relpath(src), "reason": "origem nao existe"})
            continue
        if dst.exists():
            skipped.append({"src": relpath(src), "reason": "destino ja existe"})
            print(f"  PULAR (ja existe em obsoletos/): {relpath(src)}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            moved.append({
                "src": relpath(src), "dst": relpath(dst),
                "kind": kind, "sha256": sha, "moved_at": timestamp,
            })
            print(f"  OK   [{kind:5s}] {relpath(src)}")
        except Exception as e:
            skipped.append({"src": relpath(src), "reason": str(e)})
            print(f"  FAIL [{kind:5s}] {relpath(src)}: {e}")

    # 2. __pycache__: tambem move (nao registra no manifest, sao regeneraveis)
    cache_moved = 0
    for src, dst, kind, sha in pycaches:
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            cache_moved += 1
        except Exception as e:
            print(f"  FAIL pycache {relpath(src)}: {e}")
    print(f"\n  __pycache__ movidos: {cache_moved}")

    # 3. manifest
    existing = {}
    if MANIFEST.exists():
        try:
            existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass

    runs = existing.get("runs", [])
    runs.append({
        "timestamp": timestamp,
        "moved": moved,
        "skipped": skipped,
        "pycache_moved": cache_moved,
    })

    manifest_data = {
        "version": 1,
        "project_root": str(ROOT),
        "obsoletos_dir": str(DEST),
        "runs": runs,
    }
    MANIFEST.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n=== RESUMO ===")
    print(f"Movidos:    {len(moved)}")
    print(f"Pulados:    {len(skipped)}")
    print(f"__pycache__: {cache_moved}")
    print(f"Manifest:   {MANIFEST}")
    if skipped:
        print("\nPulados (verificar manualmente):")
        for s in skipped:
            print(f"  - {s['src']}: {s['reason']}")


# ============================================================================
# Main
# ============================================================================

def main():
    ap = argparse.ArgumentParser(description="Move arquivos obsoletos para obsoletos/")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="So mostra o que seria movido")
    g.add_argument("--apply", action="store_true", help="Aplica o move de fato")
    args = ap.parse_args()

    targets = collect_targets()
    pycaches = collect_pycaches()

    if args.dry_run:
        do_dry_run(targets, pycaches)
        print("\nPara aplicar de verdade: python scripts/mover_obsoletos.py --apply")
    else:
        do_apply(targets, pycaches)
        print("\nPara reverter: python scripts/reverter_obsoletos.py --all")


if __name__ == "__main__":
    main()
