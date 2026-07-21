#!/usr/bin/env python3
"""scripts/backup_memory.py - Backup rotativo do kv_memory.db (7 dias).

Fase A do roadmap (2026-05-14): proteger o ativo `memory/agent_memory.db`
e o KV em %LOCALAPPDATA%/LILO/memory/kv_memory.db.

Estrategia:
  - Usa kv_memory.export_json() (formato textual portavel) por namespace
  - Salva em backups/kv_<YYYY-MM-DD>.json
  - Limpa snapshots com mais de N dias (default 7)

Uso:
    python scripts/backup_memory.py            # backup + cleanup
    python scripts/backup_memory.py --keep 14  # mantem 14 dias
    python scripts/backup_memory.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BACKUP_DIR = ROOT / "backups"


def _today_iso() -> str:
    return dt.date.today().isoformat()


def backup(dry_run: bool = False) -> Path:
    from shared.kv_memory import get_memory
    mem = get_memory()
    blob = mem.export_json()  # all namespaces
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    out = BACKUP_DIR / f"kv_{_today_iso()}.json"
    if dry_run:
        print(f"[DRY] escreveria {len(blob)} bytes em {out}")
    else:
        out.write_text(blob, encoding="utf-8")
        print(f"[OK]  {out}  ({len(blob)} bytes)")
    return out


def cleanup(keep_days: int, dry_run: bool = False) -> int:
    if not BACKUP_DIR.exists():
        return 0
    today = dt.date.today()
    n_removed = 0
    for p in BACKUP_DIR.glob("kv_*.json"):
        try:
            date_str = p.stem.replace("kv_", "")
            d = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        age = (today - d).days
        if age > keep_days:
            if dry_run:
                print(f"[DRY] removeria {p} (age {age}d)")
            else:
                p.unlink()
                print(f"[DEL] {p} (age {age}d)")
            n_removed += 1
    return n_removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep", type=int, default=7,
                    help="Dias para reter (default 7)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    backup(dry_run=args.dry_run)
    n = cleanup(args.keep, dry_run=args.dry_run)
    print(f"Cleanup: {n} snapshot(s) > {args.keep}d removidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
