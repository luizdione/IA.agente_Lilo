"""
lilo_mcp.py — Servidor MCP (Model Context Protocol) do LILO
=============================================================
Expõe os 4 subagentes como tools para o Claude Desktop.

Protocolo: JSON-RPC 2.0 via stdin/stdout (MCP spec 2024-11)

Configurar em %APPDATA%\\Claude\\claude_desktop_config.json:
  {
    "mcpServers": {
      "lilo": {
        "command": "python",
        "args": ["C:\\\\Users\\\\luizd\\\\OneDrive\\\\Data_Science\\\\Projetos\\\\IA.agente\\\\lilo_mcp.py"],
        "env": {
          "PYTHONPATH": "C:\\\\Users\\\\luizd\\\\OneDrive\\\\Data_Science\\\\Projetos\\\\IA.agente"
        }
      }
    }
  }
"""

import json
import sys
import traceback
from pathlib import Path

# Garante path do projeto
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.logger import get_logger
from shared.utils import load_env

load_env()
log = get_logger("MCP")

# Importa orquestrador (lazy — agents carregados na primeira chamada)
from lilo import route, health_check, _load_agents

# ── Definições de tools MCP ──────────────────────────────────────────────────

def list_tools() -> list[dict]:
    """Agrega as tools de todos os subagentes carregados."""
    agents = _load_agents()
    tools = []
    for agent in agents.values():
        try:
            tools.extend(agent.get_tools())
        except Exception as e:
            log.warning(f"Erro ao listar tools de {agent.name}: {e}")

    # Tool extra: health
    tools.append({
        "name": "lilo_health",
        "description": "Verifica status de todos os subagentes e backends LLM do LILO.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    })
    return tools


# Mapa tool_name → (tab, context_builder)
_TOOL_TAB_MAP = {
    # SQL
    "sql_query":  ("sql",     lambda a: {"db_path": a.get("db_path",""), "table": a.get("table","")}),
    "sql_stats":  ("sql",     lambda a: {"table": a.get("table","")}),
    # PDF
    "pdf_summarize": ("pdf",  lambda a: {"file_path": a.get("file_path",""), "mode": a.get("mode","simple")}),
    "pdf_search":    ("pdf",  lambda a: {}),
    "pdf_list":      ("pdf",  lambda a: {}),
    # Scholar
    "scholar_search":     ("scholar", lambda a: {"source": a.get("source","auto"), "max_results": a.get("max_results",5), "synthesize": False}),
    "scholar_synthesize": ("scholar", lambda a: {"max_results": a.get("max_results",5), "synthesize": True}),
    # Gateway
    "lilo_chat":   ("gateway", lambda a: {"mode": a.get("mode","chat"), "model": a.get("model",None)}),
    "lilo_models": ("gateway", lambda a: {"_list_models": True}),
    "lilo_health": (None,      None),
}


# ── Handler de requests ──────────────────────────────────────────────────────

def handle_request(req: dict) -> dict:
    """Processa um request JSON-RPC MCP e retorna o result."""
    method = req.get("method", "")
    params = req.get("params", {})

    # ── Inicialização do protocolo MCP ───────────────────────────────────────
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "lilo",
                "version": "1.0.0",
                "description": "LILO — Orquestrador de agentes de IA para bioinformática e ciência de dados",
            },
        }

    if method == "notifications/initialized":
        return {}  # acknowledge

    # ── Lista de tools ───────────────────────────────────────────────────────
    if method == "tools/list":
        return {"tools": list_tools()}

    # ── Execução de tool ─────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # Health especial
        if tool_name == "lilo_health":
            result = health_check()
            return {"content": [{"type": "text", "text": result}]}

        # Lookup da tool
        if tool_name not in _TOOL_TAB_MAP:
            return {
                "content": [{"type": "text", "text": f"[LILO] Tool desconhecida: {tool_name}"}],
                "isError": True,
            }

        tab, ctx_builder = _TOOL_TAB_MAP[tool_name]

        # lilo_models — caso especial
        if tool_name == "lilo_models":
            agents = _load_agents()
            gw = agents.get("gateway")
            if gw and hasattr(gw, "list_models"):
                models = gw.list_models()
                text = "Modelos disponíveis:\n" + "\n".join(f"- {m}" for m in models)
            else:
                text = "[LILO] Gateway não disponível."
            return {"content": [{"type": "text", "text": text}]}

        # Extrai query
        query = arguments.get("query", arguments.get("filter", ""))
        ctx   = ctx_builder(arguments) if ctx_builder else {}

        try:
            result = route(query, tab=tab, context=ctx)
            return {"content": [{"type": "text", "text": result}]}
        except Exception as e:
            tb = traceback.format_exc()
            log.error(f"Erro ao executar tool {tool_name}: {tb}")
            return {
                "content": [{"type": "text", "text": f"[LILO] Erro: {e}"}],
                "isError": True,
            }

    # ── Ping ─────────────────────────────────────────────────────────────────
    if method == "ping":
        return {}

    return {"error": f"Método não suportado: {method}"}


# ── Loop principal stdin/stdout ───────────────────────────────────────────────

def main():
    log.info("LILO MCP Server iniciado. Aguardando requests...")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req  = json.loads(line)
            req_id = req.get("id")
            result = handle_request(req)

            # Notificações não têm id e não precisam de resposta
            if req_id is None and req.get("method", "").startswith("notifications/"):
                continue

            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except json.JSONDecodeError as e:
            log.error(f"JSON inválido: {e}")
            resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
        except Exception as e:
            log.error(f"Erro inesperado: {traceback.format_exc()}")
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if "req" in dir() else None,
                "error": {"code": -32603, "message": str(e)},
            }

        print(json.dumps(resp, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
