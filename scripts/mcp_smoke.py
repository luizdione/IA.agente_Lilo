"""Smoke da ponte lilo-host: lista as tools de cada grupo e confere o token do exec.

    python scripts\\mcp_smoke.py                    # contra http://127.0.0.1:8790
    python scripts\\mcp_smoke.py --url http://host.docker.internal:8790   # de dentro de um container

Portao G3 (parte): /saude responde; conhecimento e analise listam tools; /exec/mcp
sem token devolve 401 e com token lista; uma chamada real (memoria_projetos_listar).
Codigo de saida 1 em qualquer falha.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def _tools(url: str, token: str | None = None) -> list[str]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers = {"Authorization": "Bearer " + token} if token else None
    async with streamablehttp_client(url, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.list_tools()
            return [t.name for t in res.tools]


async def _chamar(url: str, nome: str, args: dict) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(url) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(nome, args)
            return "".join(getattr(c, "text", "") for c in res.content)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8790")
    ap.add_argument("--token", default="", help="token do exec (padrao: o do arquivo local)")
    a = ap.parse_args()
    falhas: list[str] = []

    try:
        s = httpx.get(a.url + "/saude", timeout=10)
        print("/saude", s.status_code, s.json())
        if s.status_code != 200:
            falhas.append("/saude != 200")
    except httpx.HTTPError as e:
        print("ponte fora do ar em %s: %s" % (a.url, e))
        return 1

    for grupo in ("conhecimento", "analise"):
        try:
            nomes = asyncio.run(_tools(f"{a.url}/{grupo}/mcp"))
            print(f"{grupo}: {len(nomes)} tools -> {', '.join(nomes)}")
            if not nomes or len(nomes) > 13:
                falhas.append(f"{grupo}: {len(nomes)} tools (esperado 1..13)")
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{grupo}: {type(e).__name__}: {e}")

    r = httpx.post(f"{a.url}/exec/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                   headers={"Accept": "application/json, text/event-stream"}, timeout=10)
    print("exec sem token:", r.status_code)
    if r.status_code != 401:
        falhas.append("exec sem token devolveu %d (esperado 401)" % r.status_code)

    token = a.token
    if not token:
        from lilo_host.comum import token_exec
        token = token_exec(gerar=False)
    if token:
        try:
            nomes = asyncio.run(_tools(f"{a.url}/exec/mcp", token))
            print(f"exec com token: {len(nomes)} tools -> {', '.join(nomes)}")
        except Exception as e:  # noqa: BLE001
            falhas.append(f"exec com token: {type(e).__name__}: {e}")
    else:
        print("exec com token: pulado (sem token local; passe --token)")

    try:
        txt = asyncio.run(_chamar(f"{a.url}/conhecimento/mcp", "memoria_projetos_listar", {}))
        print("memoria_projetos_listar:", txt[:160].replace("\n", " "), "...")
    except Exception as e:  # noqa: BLE001
        falhas.append(f"chamada real: {type(e).__name__}: {e}")

    print("SMOKE: " + ("PASSOU" if not falhas else "FALHOU - " + "; ".join(falhas)))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
