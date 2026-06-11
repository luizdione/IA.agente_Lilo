#!/usr/bin/env python3
"""lilo_serve.py - Servico unificado LILO (Fase A do roadmap, 2026-05-14).

Substitui os 3 entry points historicos (lilo_mcp.py, lilo_server.py,
lilo_api.py) por um unico script com flag --transport:

    python lilo_serve.py --transport stdio   # Claude Desktop, PyCharm
    python lilo_serve.py --transport http    # Cowork, scripts batch
    python lilo_serve.py --transport sse     # Streaming clients

Os tres scripts originais continuam funcionando (compat); este e
recomendado para deploy novo.

Variaveis de ambiente:
    LILO_HOST    (default 127.0.0.1)
    LILO_PORT    (default 8088)
    LILO_TOKEN   (auth para http/sse; opcional)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _serve_stdio() -> int:
    """Roda o servidor MCP via stdio (Claude Desktop / PyCharm)."""
    try:
        from lilo_mcp import main as mcp_main
    except Exception as e:
        print(f"[lilo_serve] Falha ao carregar lilo_mcp: {e}", file=sys.stderr)
        return 1
    return int(mcp_main() or 0)


def _serve_http(host: str, port: int) -> int:
    """Roda o servidor HTTP FastAPI (lilo_api.py)."""
    # 2026-05-25: default de perfil no transporte HTTP. O transporte HTTP e
    # usado por automacao local (Cowork, scripts batch, scheduled tasks), entao
    # o perfil mais seguro e `cowork` (local-only, sem custo de nuvem). setdefault
    # respeita um LILO_SERVER_PROFILE ja exportado pelo ambiente (override).
    os.environ.setdefault("LILO_SERVER_PROFILE", "cowork")
    try:
        import uvicorn
        from lilo_api import app
    except Exception as e:
        print(f"[lilo_serve] Falha ao carregar lilo_api/uvicorn: {e}",
              file=sys.stderr)
        return 1
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def _serve_sse(host: str, port: int) -> int:
    """SSE = HTTP normal (FastAPI ja serve SSE em /v1/chat/stream)."""
    return _serve_http(host, port)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--transport", "-t",
        choices=["stdio", "http", "sse"], default="stdio",
        help="Modo de transporte: stdio (default), http ou sse"
    )
    ap.add_argument("--host", default=os.environ.get("LILO_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("LILO_PORT", "8088")))
    args = ap.parse_args()

    if args.transport == "stdio":
        return _serve_stdio()
    if args.transport == "http":
        return _serve_http(args.host, args.port)
    if args.transport == "sse":
        return _serve_sse(args.host, args.port)
    return 1


if __name__ == "__main__":
    sys.exit(main())
