"""Catalogo minimo do LILO para o Docker MCP Gateway: so o `paper-search`.

    python scripts\\gateway_catalogo.py            # escreve ~/.docker/mcp/catalogs/lilo.yaml
    python scripts\\gateway_catalogo.py --forcar   # reescreve mesmo se ja existir

Por que: na 0.43 o `docker mcp catalog create` guarda o catalogo num banco (mcp-toolkit.db),
mas `docker mcp gateway run` ainda le ARQUIVOS em ~/.docker/mcp/catalogs/ - sem o arquivo,
`--servers paper-search` sobe com "0 tools" sem reclamar. Este script tira o `paper-search`
de `docker mcp catalog show docker-mcp` (criado com --from-legacy-catalog) e grava um
catalogo no formato legado (`registry: {nome: servidor}`), que o gateway recebe em
`--catalog lilo.yaml`. O lilo.ps1 chama isto no `gateway up` quando o arquivo falta.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

CATALOGO_ORIGEM = "docker-mcp"
SERVIDORES = ("paper-search",)
DESTINO = Path.home() / ".docker" / "mcp" / "catalogs" / "lilo.yaml"


def servidores_do_catalogo(nome: str) -> dict:
    saida = subprocess.run(["docker", "mcp", "catalog", "show", nome], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    if saida.returncode != 0:
        sys.exit("docker mcp catalog show %s falhou: %s\nCrie-o com: docker mcp catalog create %s "
                 "--from-legacy-catalog https://desktop.docker.com/mcp/catalog/v2/catalog.yaml"
                 % (nome, saida.stderr.strip()[:300], nome))
    doc = yaml.safe_load(saida.stdout) or {}
    out = {}
    for item in doc.get("servers") or []:
        srv = (item.get("snapshot") or {}).get("server") or {}
        if srv.get("name"):
            out[srv["name"]] = srv
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--forcar", action="store_true")
    ap.add_argument("--destino", default=str(DESTINO))
    a = ap.parse_args()
    destino = Path(a.destino)
    if destino.exists() and not a.forcar:
        print("ja existe: %s (use --forcar para reescrever)" % destino)
        return 0
    todos = servidores_do_catalogo(CATALOGO_ORIGEM)
    faltam = [s for s in SERVIDORES if s not in todos]
    if faltam:
        sys.exit("servidores ausentes no catalogo %s: %s" % (CATALOGO_ORIGEM, ", ".join(faltam)))
    registro = {s: todos[s] for s in SERVIDORES}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(yaml.safe_dump({"registry": registro}, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
    for s in SERVIDORES:
        print("%s: %s (%d tools)" % (s, registro[s].get("image", "?"), len(registro[s].get("tools") or [])))
    print("gravado: %s" % destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
