"""
test_mcp_stdio.py -- Smoke test do MCP server LILO via stdio.

Simula o que o Claude Desktop faz ao conectar:
1. Inicia lilo_mcp.py como subprocess (stdio transport)
2. Envia handshake initialize
3. Lista tools
4. Chama lilo_health
5. Verifica resposta

Uso:
    python scripts/test_mcp_stdio.py                       # profile claude_code (default)
    python scripts/test_mcp_stdio.py --profile bio
    python scripts/test_mcp_stdio.py --profile opus

Os profiles validos sao derivados de config/profiles.yaml (+ aliases).

Saida esperada:
    [OK] initialize  -> server: lilo
    [OK] tools/list  -> N tools
    [OK] lilo_health -> ...
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Fallback caso o YAML nao exista/ilegivel: nomes embarcados em _PROFILE_TOOLS
# (lilo_mcp.py) + aliases historicos. Mantem o smoke-test util offline.
_FALLBACK_PROFILES = {
    "claude_code", "bio", "opus", "pycharm", "cowork",
    "desktop", "desktop_dev", "claude_desktop", "pycharm_assistant", "openclaw",
}


def _known_profiles() -> list[str]:
    """Profiles validos = chaves de 'profiles:' + 'aliases:' do profiles.yaml,
    unidas ao fallback embarcado. Evita que a lista de --profile envelheca
    quando novos perfis sao adicionados (ex.: 'claude_code', 'cowork')."""
    names = set(_FALLBACK_PROFILES)
    yaml_path = _ROOT / "config" / "profiles.yaml"
    try:
        import yaml as _yaml
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = _yaml.safe_load(fh) or {}
        names.update((data.get("profiles") or {}).keys())
        names.update((data.get("aliases") or {}).keys())
    except Exception:
        pass  # YAML ausente/ilegivel -> usa apenas o fallback
    return sorted(names)


def _send(proc, msg: dict):
    line = json.dumps(msg) + "\n"
    proc.stdin.write(line.encode("utf-8"))
    proc.stdin.flush()


def _read_response(proc, timeout: float = 30.0):
    """Le uma resposta JSON-RPC do stdout, ignorando linhas que nao sao JSON."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        try:
            text = line.decode("utf-8", errors="replace").strip()
        except Exception:
            continue
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # log/banner do stderr capturado por engano? ignora
            sys.stderr.write(f"[skip non-json] {text[:120]}\n")
            continue
    raise TimeoutError(f"Sem resposta em {timeout}s")


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--profile", default="claude_code", choices=_known_profiles(),
        help="Perfil MCP (fonte da verdade: config/profiles.yaml). "
             "Ex.: claude_code, bio, opus, desktop_dev.",
    )
    p.add_argument("--python", default=sys.executable, help="Python a usar")
    p.add_argument("--script", default=str(_ROOT / "lilo_mcp.py"))
    args = p.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(_ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [args.python, args.script, "--profile", args.profile]
    print(f"[run] {' '.join(cmd)}")
    print(f"[env] PYTHONPATH={env['PYTHONPATH']}")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env,
        cwd=str(_ROOT),
    )

    # 1) initialize
    _send(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "lilo-smoke-test", "version": "1.0.0"},
        },
    })
    try:
        r = _read_response(proc, timeout=15)
        if r.get("result"):
            print(f"[OK] initialize  -> server: {r['result'].get('serverInfo', {}).get('name', '?')}")
        else:
            print(f"[FAIL] initialize: {r}")
            _dump_stderr(proc)
            return 1
    except TimeoutError as e:
        print(f"[FAIL] initialize timeout: {e}")
        _dump_stderr(proc)
        return 1

    # initialized notification
    _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 2) tools/list
    _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    try:
        r = _read_response(proc, timeout=10)
        tools = r.get("result", {}).get("tools", [])
        print(f"[OK] tools/list  -> {len(tools)} tools")
        for t in tools[:5]:
            print(f"      - {t.get('name')}: {t.get('description', '')[:60]}")
        if len(tools) > 5:
            print(f"      ... +{len(tools) - 5} mais")
    except TimeoutError as e:
        print(f"[FAIL] tools/list timeout: {e}")
        _dump_stderr(proc)
        return 1

    # 3) tools/call -- escolhe uma tool apropriada para o profile.
    # Para profiles que NAO incluem lilo_health (ex: 'opus'), usa
    # outra tool leve disponivel.
    tool_names = [t.get("name") for t in tools]
    smoke_tool = None
    smoke_args: dict = {}
    for candidate, args in [
        ("lilo_health", {}),
        ("lilo_list_local_models", {}),
        ("fs_list", {"path": str(_ROOT), "glob": "*.py", "limit": 5}),
        ("lilo_memory_list", {}),
    ]:
        if candidate in tool_names:
            smoke_tool = candidate
            smoke_args = args
            break
    if smoke_tool is None:
        print("[SKIP] tools/call -- nenhuma tool de smoke disponivel no profile")
    else:
        _send(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": smoke_tool, "arguments": smoke_args},
        })
        try:
            r = _read_response(proc, timeout=120)  # health pode demorar
            if r.get("result"):
                content = r["result"].get("content", [])
                if content and content[0].get("type") == "text":
                    preview = content[0]["text"][:300]
                    print(f"[OK] {smoke_tool} -> {preview}")
                else:
                    print(f"[OK] {smoke_tool} (sem text content)")
            else:
                print(f"[FAIL] {smoke_tool}: {r}")
                _dump_stderr(proc)
                return 1
        except TimeoutError as e:
            print(f"[FAIL] {smoke_tool} timeout: {e}")
            _dump_stderr(proc)
            return 1

    print("\n[SUCCESS] Servidor MCP LILO esta funcional via stdio.")
    proc.terminate()
    return 0


def _dump_stderr(proc):
    try:
        proc.terminate()
        time.sleep(0.5)
        err = proc.stderr.read()
        if err:
            sys.stderr.write("\n--- STDERR do servidor ---\n")
            sys.stderr.write(err.decode("utf-8", errors="replace"))
            sys.stderr.write("--- fim STDERR ---\n")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
