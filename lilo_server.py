"""
lilo_server.py — LILO como servidor HTTP MCP (StreamableHTTP transport)
========================================================================
Expõe o LILO via HTTP para integração com Cowork e qualquer cliente MCP.

Uso:
    python lilo_server.py              # porta padrão 8899
    python lilo_server.py --port 8899

Registrar no Cowork:
    Settings → Capabilities → MCP Servers → Add
    URL: http://localhost:8899/mcp

Iniciar automaticamente:
    Executar start_lilo.bat antes de abrir o Cowork
"""

import argparse
import json
import sys
import traceback
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Garante path do projeto
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from shared.logger import get_logger
from shared.utils import load_env

load_env()
log = get_logger("LILOServer")

# Importa orquestrador
from lilo import route, health_check, _load_agents


# ── Tool definitions (igual ao lilo_mcp.py) ──────────────────────────────────

def list_tools() -> list[dict]:
    agents = _load_agents()
    tools = []
    for agent in agents.values():
        try:
            tools.extend(agent.get_tools())
        except Exception as e:
            log.warning(f"Erro ao listar tools de {agent.name}: {e}")

    tools.append({
        "name": "lilo_health",
        "description": "Verifica status de todos os subagentes e backends LLM do LILO.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    })
    return tools


_TOOL_TAB_MAP = {
    "sql_query":          ("sql",     lambda a: {"db_path": a.get("db_path",""), "table": a.get("table","")}),
    "sql_stats":          ("sql",     lambda a: {"table": a.get("table","")}),
    "pdf_summarize":      ("pdf",     lambda a: {"file_path": a.get("file_path",""), "mode": a.get("mode","simple")}),
    "pdf_search":         ("pdf",     lambda a: {}),
    "pdf_list":           ("pdf",     lambda a: {}),
    "scholar_search":     ("scholar", lambda a: {"source": a.get("source","auto"), "max_results": a.get("max_results",5), "synthesize": False}),
    "scholar_synthesize": ("scholar", lambda a: {"max_results": a.get("max_results",5), "synthesize": True}),
    "lilo_chat":          ("gateway", lambda a: {"mode": a.get("mode","chat"), "model": a.get("model",None)}),
    "lilo_models":        ("gateway", lambda a: {"_list_models": True}),
    "lilo_health":        (None,      None),
}


def handle_mcp_request(req: dict) -> dict:
    """Processa JSON-RPC MCP e retorna result."""
    method = req.get("method", "")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "lilo", "version": "1.0.0"},
        }

    if method in ("notifications/initialized", "ping"):
        return {}

    if method == "tools/list":
        return {"tools": list_tools()}

    if method == "tools/call":
        tool_name  = params.get("name", "")
        arguments  = params.get("arguments", {})

        if tool_name == "lilo_health":
            return {"content": [{"type": "text", "text": health_check()}]}

        if tool_name == "lilo_models":
            agents = _load_agents()
            gw = agents.get("gateway")
            models = gw.list_models() if gw and hasattr(gw, "list_models") else []
            text = "Modelos:\n" + "\n".join(f"- {m}" for m in models)
            return {"content": [{"type": "text", "text": text}]}

        if tool_name not in _TOOL_TAB_MAP:
            return {"content": [{"type": "text", "text": f"Tool desconhecida: {tool_name}"}], "isError": True}

        tab, ctx_builder = _TOOL_TAB_MAP[tool_name]
        query = arguments.get("query", arguments.get("filter", ""))
        ctx   = ctx_builder(arguments) if ctx_builder else {}

        try:
            result = route(query, tab=tab, context=ctx)
            return {"content": [{"type": "text", "text": result}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Erro: {e}"}], "isError": True}

    return {"error": f"Método não suportado: {method}"}


# ── Handler HTTP ──────────────────────────────────────────────────────────────

class MCPHandler(BaseHTTPRequestHandler):
    """Handler HTTP que implementa StreamableHTTP transport do MCP."""

    def log_message(self, fmt, *args):
        log.info(fmt % args)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/health"):
            self._send_json({"status": "ok", "server": "LILO MCP", "version": "1.0.0"})
        elif self.path == "/mcp":
            # SSE stream — responde com capabilities para clientes que fazem GET
            body = json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "lilo", "version": "1.0.0"},
                }
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/mcp":
            self._send_json({"error": "Not found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            req    = json.loads(body.decode("utf-8"))
        except Exception as e:
            self._send_json({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": str(e)}}, 400)
            return

        try:
            result = handle_mcp_request(req)
            resp   = {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
        except Exception as e:
            log.error(traceback.format_exc())
            resp = {"jsonrpc": "2.0", "id": req.get("id"),
                    "error": {"code": -32603, "message": str(e)}}

        self._send_json(resp)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LILO MCP HTTP Server")
    parser.add_argument("--port", "-p", type=int, default=8899)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # Pré-carrega agentes na inicialização
    log.info("Carregando subagentes LILO...")
    _load_agents()

    server = HTTPServer((args.host, args.port), MCPHandler)
    log.info(f"LILO MCP Server rodando em http://{args.host}:{args.port}/mcp")
    log.info("Para parar: Ctrl+C")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Servidor encerrado.")
        server.server_close()


if __name__ == "__main__":
    main()
