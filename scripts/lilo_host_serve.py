"""Lancador da ponte lilo-host (servidor MCP HTTP em 127.0.0.1:8790).

    python scripts\\lilo_host_serve.py              # sobe (bloqueia o terminal)
    python scripts\\lilo_host_serve.py --token      # so imprime o token do grupo exec
    python scripts\\lilo_host_serve.py --token-novo # gera outro token (religar a interface)

Roda no conda datascience (o lilo.ps1 ja usa esse Python). Grava
%LOCALAPPDATA%\\LILO\\host.status.json (pid, porta, inicio) para o lilo.ps1 parar
o processo; o token fica em %LOCALAPPDATA%\\LILO\\host_token.txt (LILO_HOST_TOKEN
no ambiente tem precedencia). Porta: --porta ou LILO_HOST_PORTA.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lilo_host import comum  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--porta", type=int, default=comum.PORTA)
    ap.add_argument("--token", action="store_true", help="imprime o token do exec e sai")
    ap.add_argument("--token-novo", action="store_true", help="gera um token novo e sai")
    a = ap.parse_args()

    if a.token_novo:
        comum.ARQ_TOKEN.unlink(missing_ok=True)
        os.environ.pop("LILO_HOST_TOKEN", None)
        print(comum.token_exec())
        return 0
    if a.token:
        print(comum.token_exec())
        return 0

    import uvicorn
    from lilo_host.servidor import criar_app

    comum.PORTA = a.porta
    comum.TRABALHO.mkdir(parents=True, exist_ok=True)
    app = criar_app(comum.token_exec())
    comum.ARQ_STATUS.parent.mkdir(parents=True, exist_ok=True)
    comum.ARQ_STATUS.write_text(json.dumps({"pid": os.getpid(), "porta": a.porta,
                                            "inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
                                            "python": sys.executable}), encoding="utf-8")
    print("lilo-host em http://127.0.0.1:%d  (/saude, /conhecimento/mcp, /analise/mcp, /exec/mcp)" % a.porta)
    try:
        uvicorn.run(app, host="127.0.0.1", port=a.porta, log_level="warning")
    finally:
        comum.ARQ_STATUS.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
