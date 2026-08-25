"""Cliente MCP minimo do LILO v13.1 — o LILO como CONSUMIDOR de MCP.

Allow-list explicita no .env (nada de auto-descoberta de servidores):

    LILO_MCP=nome=comando arg1 arg2;outro=python -m servidor_x

Dependencia OPCIONAL: pacote `mcp` (pip install mcp). Ausencia ou falha vira
"[ERRO] ..." instrutivo devolvido ao modelo — nunca derruba o nucleo. Exposto
ao agente pela tool `mcp` (atras do choke-point + portao, kind "mcp").
"""
from __future__ import annotations

import asyncio
import os
import shlex

from lilo import config

TIMEOUT_S = 60


def servidores() -> dict[str, list[str]]:
    """Parse de LILO_MCP -> {nome: [comando, args...]}."""
    bruto = config.get_env("LILO_MCP", "")
    out: dict[str, list[str]] = {}
    for parte in bruto.split(";"):
        parte = parte.strip()
        if not parte or "=" not in parte:
            continue
        nome, _, cmd = parte.partition("=")
        nome = nome.strip()
        try:
            args = shlex.split(cmd.strip(), posix=(os.name != "nt"))
        except ValueError:
            continue
        if nome and args:
            out[nome] = args
    return out


def _extrair_texto(resultado) -> str:
    pedacos = []
    for bloco in getattr(resultado, "content", None) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            pedacos.append(texto)
    return "\n".join(pedacos) or str(resultado)


def chamar(servidor: str, tool: str = "", argumentos: dict | None = None) -> str:
    """Chama `tool` no `servidor` configurado. Sem `tool`: lista as tools.
    Sempre retorna string ([ERRO] em qualquer falha)."""
    srv = servidores()
    if servidor not in srv:
        return "[ERRO] servidor MCP desconhecido: %r. Configurados: %s" % (
            servidor, ", ".join(srv) or "(nenhum — defina LILO_MCP no .env)")
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        return ("[ERRO] pacote 'mcp' nao instalado — rode: pip install mcp "
                "(dependencia opcional do LILO)")

    cmd = srv[servidor]
    params = StdioServerParameters(command=cmd[0], args=cmd[1:])

    async def _rodar():
        async with stdio_client(params) as (leitura, escrita):
            async with ClientSession(leitura, escrita) as sessao:
                await sessao.initialize()
                if not tool:
                    resp = await sessao.list_tools()
                    linhas = ["%s — %s" % (t.name, (t.description or "")[:120])
                              for t in resp.tools]
                    return "\n".join(linhas) or "(servidor sem tools)"
                resultado = await sessao.call_tool(tool, argumentos or {})
                return _extrair_texto(resultado)

    try:
        return asyncio.run(asyncio.wait_for(_rodar(), timeout=TIMEOUT_S))
    except Exception as e:  # noqa: BLE001 — erro externo volta ao modelo
        return "[ERRO] MCP %s: %s: %s" % (servidor, type(e).__name__, e)
