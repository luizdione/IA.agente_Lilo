"""
scripts/reverter_obsoletos.py
=============================
Le obsoletos/manifest.json e move arquivos de volta para suas origens.

Uso:
    python scripts/reverter_obsoletos.py --all              # reverte tudo
    python scripts/reverter_obsoletos.py --file <caminho>   # reverte um especifico
    python scripts/reverter_obsoletos.py --list             # so lista o que tem em obsoletos
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "obsoletos"
MANIFEST = DEST / "manifest.json"


def sha256_of(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    if not MANIFEST.exists():
        sys.stderr.write("ERRO: manifest.json nao encontrado em obsoletos/\n")
        sys.exit(1)
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def all_moved_entries(manifest):
    """Achata todos os 'moved' de todas as runs em uma lista."""
    out = []
    for run in manifest.get("runs", []):
        for m in run.get("moved", []):
            out.append(m)
    return out


def revert_one(entry, force=False):
    src = ROOT / entry["dst"]    # "dst" do manifest = onde esta agora
    dst = ROOT / entry["src"]    # "src" do manifest = origem original
    if not src.exists():
        print(f"  PULAR (nao existe em obsoletos): {entry['src']}")
        return False
    if dst.exists():
        if force:
            print(f"  SOBRESCREVER: {entry['src']}")
            if dst.is_file():
                dst.unlink()
            else:
                shutil.rmtree(dst)
        else:
            print(f"  PULAR (origem ja existe; --force para sobrescrever): {entry['src']}")
            return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(src), str(dst))
        print(f"  OK   {entry['src']}")
        return True
    except Exception as e:
        print(f"  FAIL {entry['src']}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Reverte arquivos de obsoletos/ para origem")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Reverte todos do manifest")
    g.add_argument("--file", type=str, help="Reverte um arquivo especifico (caminho relativo)")
    g.add_argument("--list", action="store_true", help="Lista o que esta em obsoletos/")
    ap.add_argument("--force", action="store_true",
                    help="Sobrescreve se ja existir na origem (CUIDADO)")
    args = ap.parse_args()

    manifest = load_manifest()
    entries = all_moved_entries(manifest)

    if args.list:
        print(f"=== Conteudo de obsoletos/ ({len(entries)} entradas) ===\n")
        for e in entries:
            cur = ROOT / e["dst"]
            mark = "OK" if cur.exists() else "MISSING"
            print(f"  [{mark}] {e['src']}  (movido em {e.get('moved_at','?')})")
        return

    if args.file:
        targets = [e for e in entries if e["src"] == args.file.replace("\\", "/")]
        if not targets:
            print(f"Nao encontrei '{args.file}' no manifest.")
            sys.exit(1)
    else:
        # --all: do mais recente para o mais antigo (LIFO)
        targets = list(reversed(entries))

    print(f"=== REVERTENDO {len(targets)} entrada(s) ===\n")
    ok = sum(1 for e in targets if revert_one(e, force=args.force))
    print(f"\n=== {ok}/{len(targets)} revertidos ===")
    if ok < len(targets):
        print("Use --force para sobrescrever destinos que ja existem.")


if __name__ == "__main__":
    main()
