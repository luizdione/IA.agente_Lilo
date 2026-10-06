"""Presets do LILO na Open WebUI, pela API. Idempotente: rode quantas vezes quiser.

    python scripts\\owui_presets.py            # cria ou atualiza os presets
    python scripts\\owui_presets.py --listar   # o que a interface expoe hoje

Sem login (D-0015): o token vem de /api/v1/auths/signin sem senha. Preset e um
registro de modelo no volume da interface (sobrevive a restart); a configuracao
em si (lista de modelos, geracoes de fundo, think:false) vive no compose.yaml.

Presets do plano v14:
  LILO           o proprio `lilo:latest`, so renomeado. Sem tools, sem thinking:
                 e o caminho do "2+2".
  LILO Pesquisa  `lilo-pesquisa` sobre o `lilo`: biblioteca, memoria dos projetos,
                 literatura e busca web (tools ligadas na F2 e na F4).
  LILO Analise   `lilo-analise` sobre o `lilo`: estatistica, parsers bio, Python,
                 R e WSL no host; SEM web (tools ligadas na F2). Conteudo da
                 internet nunca fica no mesmo preset que executa codigo.
As tools entram aqui, em TOOLS, quando a ponte lilo-host existir.
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx

BASE = os.environ.get("LILO_WEBUI", "http://127.0.0.1:3000")

# Ids de tools por preset (chaves de TOOL_SERVER_CONNECTIONS). Vazio ate a F2/F4.
TOOLS: dict[str, list[str]] = {"lilo-pesquisa": [], "lilo-analise": []}

PRESETS = (
    {
        "id": "lilo:latest", "base_model_id": None, "name": "LILO",
        "meta": {"description": "Chat rápido local (qwen3:14b, contexto 8192, sem thinking). "
                                "Para raciocínio profundo, ligue o thinking na conversa.",
                 "tags": [{"name": "local"}]},
        "params": {},
    },
    {
        "id": "lilo-pesquisa", "base_model_id": "lilo:latest", "name": "LILO Pesquisa",
        "meta": {"description": "Biblioteca de PDFs, memória dos projetos, literatura "
                                "(PubMed etc.) e busca web.",
                 "tags": [{"name": "local"}, {"name": "pesquisa"}]},
        "params": {"system": "Você é o LILO em modo Pesquisa. Responda em português. Quando a "
                             "pergunta pedir fontes, use as ferramentas de biblioteca e de "
                             "literatura e cite o que encontrar (título, autores, ano). Se não "
                             "encontrar, diga que não encontrou; não invente referências."},
    },
    {
        "id": "lilo-analise", "base_model_id": "lilo:latest", "name": "LILO Análise",
        "meta": {"description": "Estatística, parsers bio e execução de Python, R e WSL no "
                                "host. Sem internet.",
                 "tags": [{"name": "local"}, {"name": "analise"}]},
        "params": {"system": "Você é o LILO em modo Análise. Responda em português. Para contas, "
                             "estatística e arquivos use as ferramentas de análise e execução; "
                             "mostre o código ou comando que rodou e o resultado tal como veio. "
                             "Não invente números."},
    },
)


def token(cli: httpx.Client) -> str:
    r = cli.post(f"{BASE}/api/v1/auths/signin", json={"email": "", "password": ""})
    if r.status_code != 200:
        sys.exit(f"signin sem senha falhou ({r.status_code}): a interface esta com login? "
                 "O compose roda com WEBUI_AUTH=False (D-0015).")
    cli.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return r.json()["token"]


def existe(cli: httpx.Client, id_: str) -> bool:
    r = cli.get(f"{BASE}/api/v1/models/model", params={"id": id_})
    return r.status_code == 200 and bool(r.json())


def aplicar(cli: httpx.Client, preset: dict) -> str:
    meta = dict(preset["meta"])
    if preset["id"] in TOOLS:
        meta["toolIds"] = TOOLS[preset["id"]]
    form = {"id": preset["id"], "base_model_id": preset["base_model_id"],
            "name": preset["name"], "meta": meta, "params": preset["params"],
            "is_active": True}
    if existe(cli, preset["id"]):
        r = cli.post(f"{BASE}/api/v1/models/model/update", params={"id": preset["id"]}, json=form)
        acao = "atualizado"
    else:
        r = cli.post(f"{BASE}/api/v1/models/create", json=form)
        acao = "criado"
    if r.status_code != 200:
        sys.exit(f"{preset['id']}: {r.status_code} {r.text[:300]}")
    return acao


def listar(cli: httpx.Client) -> None:
    r = cli.get(f"{BASE}/api/models")
    r.raise_for_status()
    print("Modelos que a interface expoe:")
    for m in r.json().get("data", []):
        info = m.get("info") or {}
        base = info.get("base_model_id")
        print(f"  {m['id']:<30} {m.get('name', ''):<16}" + (f" (sobre {base})" if base else ""))


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
        for p in PRESETS:
            print(f"  {p['name']:<14} {aplicar(cli, p)}")
        listar(cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
