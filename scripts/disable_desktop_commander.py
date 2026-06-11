"""scripts/disable_desktop_commander.py
========================================
Desliga o Desktop Commander (DC) no claude_desktop_config.json do usuario
(salvo em %APPDATA%\\Claude\\), preservando os demais mcpServers e fazendo
backup .bak antes da modificacao.

Pos-otimizacao 2026-05-12: o profile 'opus' do lilo_mcp.py consome ~2400
tokens no system prompt e cobre todo o uso interativo. Manter DC ao lado
duplica fs_*/run_* (overhead de ~2077 tokens/chamada sem ganho real).

Uso:
    python scripts/disable_desktop_commander.py           # desliga DC
    python scripts/disable_desktop_commander.py --check   # so mostra estado
    python scripts/disable_desktop_commander.py --restore # restaura do .bak

Codigos de saida: 0 OK, 1 erro, 2 nao aplicavel.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

APPDATA = os.environ.get("APPDATA", "")
if not APPDATA:
    print("[ERRO] APPDATA nao definido (este script e Windows-only).")
    sys.exit(2)

CONFIG = Path(APPDATA) / "Claude" / "claude_desktop_config.json"
BACKUP = CONFIG.with_suffix(".json.bak")

# Nomes mais comuns sob os quais o DC e instalado no Claude Desktop.
DC_KEYS = {
    "desktop-commander", "desktop_commander", "desktopcommander",
    "@wonderwhy-er/desktop-commander", "desktopcommanderMCP",
}


def load() -> dict:
    if not CONFIG.exists():
        print(f"[ERRO] {CONFIG} nao existe -- Claude Desktop nunca foi configurado?")
        sys.exit(2)
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def save(cfg: dict):
    shutil.copy2(CONFIG, BACKUP)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"[OK] backup gravado em {BACKUP}")


def cmd_check():
    cfg = load()
    servers = cfg.get("mcpServers", {})
    print(f"mcpServers configurados ({len(servers)}):")
    for name in servers:
        marker = "  <- DC alvo" if name.lower() in DC_KEYS else ""
        print(f"  - {name}{marker}")
    found = [n for n in servers if n.lower() in DC_KEYS]
    if found:
        print(f"\n[ATENCAO] Desktop Commander detectado: {found}")
        print("Rode sem --check para desligar.")
    else:
        print("\n[OK] Desktop Commander nao esta ativo.")


def cmd_disable():
    cfg = load()
    servers = cfg.get("mcpServers", {})
    found = [n for n in servers if n.lower() in DC_KEYS]
    if not found:
        print("[OK] Desktop Commander ja desligado / nao instalado.")
        return
    for name in found:
        del servers[name]
        print(f"[OK] removido mcpServers.{name}")
    save(cfg)
    print(f"[OK] {CONFIG} atualizado. REINICIE o Claude Desktop "
          "(fechar pela bandeja) para o cache de tools ser invalidado.")


def cmd_restore():
    if not BACKUP.exists():
        print(f"[ERRO] backup nao encontrado em {BACKUP}")
        sys.exit(1)
    shutil.copy2(BACKUP, CONFIG)
    print(f"[OK] restaurado a partir de {BACKUP}")


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true",
                   help="So lista os mcpServers; nao modifica nada.")
    g.add_argument("--restore", action="store_true",
                   help="Restaura claude_desktop_config.json do .bak.")
    args = p.parse_args()
    if args.check:
        cmd_check()
    elif args.restore:
        cmd_restore()
    else:
        cmd_disable()


if __name__ == "__main__":
    main()
