"""Instala/atualiza os filtros do LILO na Open WebUI (pasta owui_funcoes/), pela API. Idempotente.

    python scripts\\owui_funcoes.py            # cria ou atualiza, ativa e torna globais
    python scripts\\owui_funcoes.py --listar   # o que a interface tem hoje

Cada arquivo owui_funcoes/<nome>.py vira a funcao `lilo_<nome>` (tipo filter): com `toggle = True`
e `icon` ela aparece como BOTAO na barra da caixa de mensagem; `UserValves` aparecem no painel
direito (Controles > Valves). Globais = valem para todos os modelos/presets.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PASTA = ROOT / "owui_funcoes"
BASE = os.environ.get("LILO_WEBUI", "http://127.0.0.1:3000")


def _meta(texto: str, chave: str) -> str:
    m = re.search(r"^%s:\s*(.+)$" % chave, texto, re.MULTILINE)
    return m.group(1).strip() if m else ""


def token(cli: httpx.Client) -> None:
    r = cli.post(f"{BASE}/api/v1/auths/signin", json={"email": "", "password": ""})
    if r.status_code != 200:
        sys.exit("signin sem senha falhou (%d): a interface esta com login?" % r.status_code)
    cli.headers["Authorization"] = "Bearer " + r.json()["token"]


def existente(cli: httpx.Client, id_: str) -> dict | None:
    r = cli.get(f"{BASE}/api/v1/functions/id/{id_}")
    return r.json() if r.status_code == 200 and r.json() else None


def aplicar(cli: httpx.Client, arq: Path) -> str:
    texto = arq.read_text(encoding="utf-8")
    id_ = "lilo_" + arq.stem
    form = {"id": id_, "name": _meta(texto, "title") or arq.stem, "content": texto,
            "meta": {"description": _meta(texto, "description")}}
    atual = existente(cli, id_)
    if atual:
        r = cli.post(f"{BASE}/api/v1/functions/id/{id_}/update", json=form)
        acao = "atualizado"
    else:
        r = cli.post(f"{BASE}/api/v1/functions/create", json=form)
        acao = "criado"
    if r.status_code != 200:
        return "%s %d %s" % (id_, r.status_code, r.text[:160])
    atual = existente(cli, id_) or {}
    if not atual.get("is_active"):
        cli.post(f"{BASE}/api/v1/functions/id/{id_}/toggle")
        acao += ", ativado"
    if not atual.get("is_global"):
        cli.post(f"{BASE}/api/v1/functions/id/{id_}/toggle/global")
        acao += ", global"
    return "%s %s" % (id_, acao)


def listar(cli: httpx.Client) -> None:
    r = cli.get(f"{BASE}/api/v1/functions/")
    r.raise_for_status()
    for f in r.json():
        print("  %-22s %-36s ativo=%s global=%s" % (f["id"], f["name"][:36], f.get("is_active"), f.get("is_global")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    with httpx.Client(timeout=60) as cli:
        try:
            token(cli)
        except httpx.ConnectError:
            sys.exit(f"Interface fora do ar em {BASE}. Suba com:  .\\lilo.ps1 up")
        if a.listar:
            listar(cli)
            return 0
        for arq in sorted(PASTA.glob("*.py")):
            print("  " + aplicar(cli, arq))
        listar(cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
