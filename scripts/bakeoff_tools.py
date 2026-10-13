"""Bake-off de tools: o modelo escolhe a ferramenta certa da ponte lilo-host?

    python scripts\\bakeoff_tools.py                          # lilo e lilo-gemma, os dois caminhos
    python scripts\\bakeoff_tools.py --modelos lilo --caminho ollama

Caminhos medidos:
  ollama  /api/chat com `tools` = schemas reais dos 3 grupos da ponte (function calling nativo).
  webui   /api/chat/completions da Open WebUI com `tool_ids` dos presets (caminho real da UI;
          sem laco de tools na API: a resposta traz os tool_calls ou o texto final).
Cada pedido tem uma tool esperada (ou nenhuma, no "2+2": chamar tool ali e erro). Respeita o
interruptor de GPU. Saida: tabela por modelo/caminho + acertos; codigo 1 se algum modelo
errar mais de 2 pedidos no caminho ollama.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402

from lilo_host.comum import OLLAMA, gpu_reservada, token_exec  # noqa: E402

PONTE = "http://127.0.0.1:8790"
WEBUI = "http://127.0.0.1:3000"
GRUPOS = ("conhecimento", "analise", "exec")
TOOL_IDS = ["server:mcp:analise", "server:mcp:exec", "server:mcp:conhecimento"]

# (pedido em PT, tool esperada ou None, trecho que os argumentos devem conter)
PEDIDOS = (
    ("Quanto é 2+2?", None, ""),
    ("Rode em Python: print(sum(range(1, 101)))", "executar_python", "range"),
    ("Rode em R: mean(c(1, 2, 3, 4))", "executar_r", "mean"),
    ("No WSL, rode o comando: uname -a", "executar_wsl", "uname"),
    ("Faça um teste t entre os grupos A = [1, 2, 3, 4, 5] e B = [3, 4, 5, 6, 7]", "estat_teste_t", "3"),
    ("Procure na minha biblioteca de PDFs trechos sobre dengue e a proteína NS1", "biblioteca_buscar", "NS1"),
    ("Liste os repositórios git que tenho em C:\\GitHub", "repos_listar", ""),
    ("Mostre o status do repositório LILO em C:\\GitHub com git", "executar_git", "status"),
)


async def _schemas() -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    out = []
    for g in GRUPOS:
        headers = {"Authorization": "Bearer " + token_exec(gerar=False)} if g == "exec" else None
        async with streamablehttp_client(f"{PONTE}/{g}/mcp", headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                for t in (await s.list_tools()).tools:
                    out.append({"type": "function", "function": {
                        "name": t.name, "description": t.description or "",
                        "parameters": t.inputSchema}})
    return out


def _ollama(cli: httpx.Client, modelo: str, pedido: str, tools: list[dict]) -> tuple[list, str, float]:
    t0 = time.perf_counter()
    r = cli.post(f"{OLLAMA}/api/chat", json={
        "model": modelo, "stream": False, "think": False, "tools": tools,
        "messages": [{"role": "user", "content": pedido}]})
    r.raise_for_status()
    m = r.json()["message"]
    calls = [(c["function"]["name"], c["function"].get("arguments") or {}) for c in m.get("tool_calls") or []]
    return calls, m.get("content") or "", time.perf_counter() - t0


def _token_webui(cli: httpx.Client) -> None:
    r = cli.post(f"{WEBUI}/api/v1/auths/signin", json={"email": "", "password": ""})
    r.raise_for_status()
    cli.headers["Authorization"] = "Bearer " + r.json()["token"]


def _webui(cli: httpx.Client, modelo: str, pedido: str) -> tuple[list, str, float]:
    t0 = time.perf_counter()
    r = cli.post(f"{WEBUI}/api/chat/completions", json={
        "model": modelo, "stream": False, "tool_ids": TOOL_IDS,
        "messages": [{"role": "user", "content": pedido}]})
    r.raise_for_status()
    d = r.json()
    m = (d.get("choices") or [{}])[0].get("message") or {}
    calls = []
    for c in m.get("tool_calls") or []:
        args = c["function"].get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {"_raw": args}
        calls.append((c["function"]["name"], args))
    return calls, m.get("content") or "", time.perf_counter() - t0


def _confere(calls: list, esperada: str | None, trecho: str, conteudo: str) -> tuple[bool, str]:
    nomes = [re.sub(r"^(conhecimento|analise|exec)_", "", n) for n, _ in calls]
    if esperada is None:
        return (not calls, "sem tool" if not calls else "chamou " + ",".join(nomes))
    if not calls:
        # Na UI o laco executa a tool e o texto final pode citar o resultado; na API crua, nao.
        return (False, "sem tool_call: " + " ".join(conteudo.split())[:60])
    ok = esperada in nomes and (not trecho or trecho in json.dumps(calls, ensure_ascii=False))
    return (ok, ",".join(nomes) + ("" if ok else " args=" + json.dumps(calls[0][1], ensure_ascii=False)[:60]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modelos", default="lilo,lilo-gemma")
    ap.add_argument("--caminho", choices=("ollama", "webui", "ambos"), default="ambos")
    a = ap.parse_args()
    motivo = gpu_reservada()
    if motivo:
        print("GPU reservada (%s): nao carrego modelo." % motivo)
        return 1
    tools = asyncio.run(_schemas())
    print("tools da ponte: %d" % len(tools))
    falhou = False
    with httpx.Client(timeout=300) as cli:
        if a.caminho in ("webui", "ambos"):
            _token_webui(cli)
        for modelo in a.modelos.split(","):
            for caminho in (("ollama", "webui") if a.caminho == "ambos" else (a.caminho,)):
                nome = modelo if caminho == "ollama" else (modelo if ":" in modelo else modelo + ":latest")
                print("\n=== %s / %s" % (caminho, nome))
                acertos, tempos = 0, []
                for pedido, esperada, trecho in PEDIDOS:
                    try:
                        calls, conteudo, seg = (_ollama(cli, nome, pedido, tools) if caminho == "ollama"
                                                else _webui(cli, nome, pedido))
                    except httpx.HTTPError as e:
                        calls, conteudo, seg = [], "ERRO HTTP %s" % e, 0.0
                    ok, detalhe = _confere(calls, esperada, trecho, conteudo)
                    acertos += ok
                    tempos.append(seg)
                    print("  %s %5.1fs  %-22s -> %s" % ("OK " if ok else "ERR", seg, (esperada or "(nenhuma)"), detalhe))
                print("  acertos %d/%d | tempo medio %.1fs" % (acertos, len(PEDIDOS), sum(tempos) / len(tempos)))
                if caminho == "ollama" and len(PEDIDOS) - acertos > 2:
                    falhou = True
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
