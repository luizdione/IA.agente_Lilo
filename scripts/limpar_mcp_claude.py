"""Remove do Claude Desktop os servidores MCP do LILO legado (v12).

Rode NA MAQUINA WINDOWS:

    python scripts\\limpar_mcp_claude.py

O que faz: abre %APPDATA%\\Claude\\claude_desktop_config.json, localiza em
mcpServers as entradas do LILO antigo (nome contendo "lilo", ou comando/args
apontando para IA.agente_Lilo / lilo_mcp), faz BACKUP do arquivo e as remove.
Idempotente: sem entradas do LILO, nao mexe em nada. Depois feche e reabra o
Claude Desktop para aplicar.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def _eh_do_lilo(nome: str, spec) -> bool:
    if "lilo" in nome.lower():
        return True
    blob = json.dumps(spec, ensure_ascii=False).lower()
    return "ia.agente_lilo" in blob or "lilo_mcp" in blob or "lilo_serve" in blob


def main() -> int:
    if os.name != "nt":
        print("Este script edita o config do Claude Desktop do WINDOWS.")
        print("Rode na sua maquina: python scripts\\limpar_mcp_claude.py")
        return 1

    cfg = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    if not cfg.exists():
        print("Nada a fazer: %s nao existe." % cfg)
        return 0

    try:
        dados = json.loads(cfg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as e:
        print("[ERRO] config ilegivel (%s) — nao vou tocar nele: %s" % (e, cfg))
        return 1

    servers = dados.get("mcpServers") or {}
    mortos = [n for n, s in servers.items() if _eh_do_lilo(n, s)]
    if not mortos:
        print("Nenhum servidor MCP do LILO no config — ja esta limpo.")
        return 0

    backup = cfg.with_name(cfg.name + ".bak_lilo")
    shutil.copy2(cfg, backup)
    for n in mortos:
        del servers[n]
    dados["mcpServers"] = servers
    cfg.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print("Removidos de mcpServers: %s" % ", ".join(mortos))
    print("Backup salvo em: %s" % backup)
    print("Feche e reabra o Claude Desktop para aplicar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
