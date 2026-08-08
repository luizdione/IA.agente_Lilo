"""shared/mcp_client.py — Cliente MCP mínimo (V18.6 E6).

Até a V18.5 o LILO era só SERVIDOR MCP; este módulo o torna CLIENTE de
servidores MCP EXTERNOS (github, filesystem, fetch...), destravando o
ecossistema sem escrever integrações próprias (item E6 da análise Open
Agent Studio).

Filosofia (espelha a allow-list de paths do desktop): allow-list DUPLA em
config/mcp/clients.yaml — só servidores listados E habilitados, e só as
tools permitidas por servidor. NADA é conectado até uma chamada explícita
(sem injeção dinâmica das tools externas no servidor MCP do LILO — evita
explosão de superfície). Import de `mcp` é LAZY: pacote ausente ou servidor
offline vira string de erro, nunca crash. Exposto ao Worker do Villa e ao
desktop via a tool interna `mcp_call`.
"""
from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Optional

from .logger import get_logger
from .utils import PROJECT_ROOT

log = get_logger("MCPClient")

CLIENTS_CONFIG = PROJECT_ROOT / "config" / "mcp" / "clients.yaml"
_CALL_TIMEOUT = 30.0  # teto por chamada (s)


def _load_config() -> dict:
    """Lê config/mcp/clients.yaml -> {servers: {...}}. Vazio se ausente."""
    try:
        import yaml
        if not CLIENTS_CONFIG.exists():
            return {}
        data = yaml.safe_load(CLIENTS_CONFIG.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.debug("clients.yaml ilegivel: %s", e)
        return {}


def _server_spec(server: str) -> tuple[Optional[dict], str]:
    """Spec de um servidor habilitado; (None, motivo) se barrado."""
    servers = (_load_config().get("servers") or {})
    spec = servers.get(server)
    if not spec or not isinstance(spec, dict):
        disponiveis = ", ".join(sorted(servers)) or "(nenhum)"
        return None, (f"servidor '{server}' nao esta na allow-list "
                      f"(config/mcp/clients.yaml). Disponiveis: {disponiveis}")
    if not spec.get("enabled", False):
        return None, f"servidor '{server}' existe mas esta enabled: false"
    if not spec.get("command"):
        return None, f"servidor '{server}' sem 'command' definido"
    return spec, ""


def _tool_allowed(spec: dict, tool: str) -> tuple[bool, str]:
    """Allow-list de tools do servidor. `tools` ausente/null = todas."""
    allow = spec.get("tools")
    if allow is None:
        return True, ""
    if isinstance(allow, list) and tool in allow:
        return True, ""
    return False, (f"tool '{tool}' fora da allow-list do servidor "
                   f"(permitidas: {', '.join(allow) if allow else '(nenhuma)'})")


def list_servers() -> list[dict]:
    """Servidores declarados + estado (sem conectar em nada)."""
    servers = (_load_config().get("servers") or {})
    out = []
    for name, spec in sorted(servers.items()):
        if not isinstance(spec, dict):
            continue
        tools = spec.get("tools")
        out.append({
            "server": name,
            "enabled": bool(spec.get("enabled", False)),
            "command": spec.get("command", ""),
            "tools": "todas" if tools is None else list(tools),
        })
    return out


def _run_async(coro_factory):
    """Roda uma corrotina em thread dedicada (asyncio.run isolado).

    Evita o 'loop already running' quando chamado de dentro de um contexto
    async (ex.: lilo_api/FastAPI) — o cliente MCP e sync-callable de qualquer
    lugar. Timeout duro por chamada."""
    def _worker():
        import asyncio
        return asyncio.run(coro_factory())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_worker).result(timeout=_CALL_TIMEOUT + 5)


async def _acall(spec: dict, tool: str, args: dict) -> str:
    """Conecta ao servidor via stdio, chama a tool e devolve texto."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(
        command=spec["command"],
        args=list(spec.get("args", []) or []),
        env=(spec.get("env") or None),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args or {})
    # result.content: lista de blocos; junta o texto dos TextContent.
    partes = []
    for bloco in getattr(result, "content", []) or []:
        txt = getattr(bloco, "text", None)
        if txt:
            partes.append(txt)
    return "\n".join(partes) if partes else "[mcp] (resposta sem texto)"


async def _alist(spec: dict) -> list[str]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(
        command=spec["command"],
        args=list(spec.get("args", []) or []),
        env=(spec.get("env") or None),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
    return [t.name for t in getattr(resp, "tools", []) or []]


def _mcp_available() -> tuple[bool, str]:
    import importlib.util as ilu
    if ilu.find_spec("mcp") is None:
        return False, "[mcp] pacote 'mcp' nao instalado (pip install mcp)"
    return True, ""


def call_tool(server: str, tool: str, args: Optional[dict] = None) -> str:
    """Chama uma tool de um servidor MCP externo (allow-list dupla)."""
    spec, motivo = _server_spec(server)
    if spec is None:
        return f"[mcp] {motivo}"
    ok, motivo = _tool_allowed(spec, tool)
    if not ok:
        return f"[mcp] {motivo}"
    disp, msg = _mcp_available()
    if not disp:
        return msg
    try:
        return _run_async(lambda: _acall(spec, tool, args or {}))
    except concurrent.futures.TimeoutError:
        return f"[mcp] timeout ({_CALL_TIMEOUT}s) chamando {server}.{tool}"
    except Exception as e:
        return f"[mcp] falha em {server}.{tool}: {str(e)[:200]}"


def list_tools(server: str) -> str:
    """Lista as tools reais de um servidor (conecta uma vez)."""
    spec, motivo = _server_spec(server)
    if spec is None:
        return f"[mcp] {motivo}"
    disp, msg = _mcp_available()
    if not disp:
        return msg
    try:
        nomes = _run_async(lambda: _alist(spec))
        allow = spec.get("tools")
        if allow is not None:
            nomes = [n for n in nomes if n in allow]
        return "[mcp] %s: %s" % (server, ", ".join(nomes) or "(nenhuma)")
    except concurrent.futures.TimeoutError:
        return f"[mcp] timeout ({_CALL_TIMEOUT}s) listando {server}"
    except Exception as e:
        return f"[mcp] falha ao listar {server}: {str(e)[:200]}"
