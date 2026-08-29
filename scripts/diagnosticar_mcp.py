"""Diagnostico da ponte LILO <-> Claude Code (v13.9).

Quando o `claude mcp` falha, a mensagem que chega ao usuario costuma ser
generica ("failed to connect"). Este script nomeia a causa: versoes e
CAMINHOS reais, um HANDSHAKE JSON-RPC de verdade contra o
`python -m lilo mcp-serve` (envia `initialize` e le a resposta), o que o
Claude Code pensa do servidor (`claude mcp list/get`) e o fim do log.

    python scripts\\diagnosticar_mcp.py              # relatorio completo
    python scripts\\diagnosticar_mcp.py --handshake  # so o teste do servidor
    python scripts\\diagnosticar_mcp.py --cmd <prog> <args...>   # comando exato

Sai com 0 se o handshake passou; 1 se nao (o conectar_claude_code.ps1 usa
isso para nao registrar um servidor quebrado).
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

HANDSHAKE_TIMEOUT_S = 30.0
PROTOCOLO = "2024-11-05"


# --- partes puras (testadas hermeticamente) ---------------------------------
def frame_initialize(id_: int = 1) -> str:
    """A 1a mensagem que todo cliente MCP manda por stdio (JSON-RPC)."""
    return json.dumps({
        "jsonrpc": "2.0", "id": id_, "method": "initialize",
        "params": {"protocolVersion": PROTOCOLO, "capabilities": {},
                   "clientInfo": {"name": "lilo-diagnostico",
                                  "version": "1.0"}}}, ensure_ascii=False)


def interpretar_resposta(linha: str) -> tuple[bool, str]:
    """(ok, explicacao) para a 1a linha que o servidor devolveu."""
    linha = (linha or "").strip()
    if not linha:
        return False, ("o servidor nao respondeu nada (subiu e morreu, ou "
                       "travou antes do handshake)")
    try:
        msg = json.loads(linha)
    except json.JSONDecodeError:
        return False, ("a 1a linha do servidor NAO e JSON — algo escreveu em "
                       "stdout e corrompeu o protocolo: %r" % linha[:200])
    if "error" in msg:
        return False, "o servidor respondeu com erro: %s" % json.dumps(
            msg["error"], ensure_ascii=False)[:300]
    resultado = msg.get("result")
    if not isinstance(resultado, dict):
        return False, "resposta sem `result`: %r" % linha[:200]
    info = resultado.get("serverInfo") or {}
    return True, "servidor '%s' respondeu o handshake (protocolo %s)" % (
        info.get("name", "?"), resultado.get("protocolVersion", "?"))


# --- handshake real ---------------------------------------------------------
def comando_padrao() -> list[str]:
    """O comando dash-free que o conectar_claude_code.ps1 registra quando nao
    ha `lilo.exe` (v13.10): <python> <repo>/scripts/servir_mcp.py."""
    return [sys.executable, str(RAIZ / "scripts" / "servir_mcp.py")]


def handshake(cmd: list[str] | None = None,
              timeout: float = HANDSHAKE_TIMEOUT_S) -> tuple[bool, str, str]:
    """Sobe o servidor MCP, manda `initialize`, le a resposta.
    `cmd` = a linha de comando EXATA que sera registrada no Claude Code
    (assim o autoteste valida o mesmo caminho que vai rodar de verdade).
    Retorna (ok, explicacao, stderr_do_servidor)."""
    cmd = list(cmd) if cmd else comando_padrao()
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", cwd=str(RAIZ))
    except OSError as e:
        return False, "nao consegui executar %s: %s" % (" ".join(cmd), e), ""

    primeira: list[str] = []

    def ler_uma_linha():
        try:
            linha = proc.stdout.readline()
        except (OSError, ValueError):
            linha = ""
        primeira.append(linha)

    leitor = threading.Thread(target=ler_uma_linha, daemon=True)
    leitor.start()
    try:
        proc.stdin.write(frame_initialize() + "\n")
        proc.stdin.flush()
    except (OSError, ValueError):
        pass  # servidor ja morreu; o stderr abaixo explica
    leitor.join(timeout)

    proc.terminate()
    try:
        _, err = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, err = proc.communicate()

    if not primeira:
        return (False, "o servidor nao respondeu em %.0fs (timeout)" % timeout,
                err or "")
    ok, explicacao = interpretar_resposta(primeira[0])
    return ok, explicacao, (err or "")


# --- relatorio --------------------------------------------------------------
def _rodar(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        return ((r.stdout or "") + (r.stderr or "")).strip() or "(sem saida)"
    except (OSError, subprocess.TimeoutExpired) as e:
        return "(nao executou: %s)" % e


def _versao_pacote(nome: str) -> str:
    try:
        import importlib.metadata as md
        return md.version(nome)
    except Exception:  # noqa: BLE001 — diagnostico nunca derruba
        return "AUSENTE"


def relatorio(cmd_extra: list[str] | None = None) -> int:
    print("=== Diagnostico LILO <-> Claude Code =========================")
    print("Python........: %s" % sys.executable)
    print("Versao Python.: %s" % sys.version.split()[0])
    print("Repo..........: %s" % RAIZ)
    try:
        from lilo import __version__
        print("LILO..........: v%s (importado de %s)"
              % (__version__, Path(sys.modules["lilo"].__file__).parent))
    except ImportError as e:
        print("LILO..........: NAO IMPORTA (%s) -> rode: pip install -e ." % e)
    print("pacote mcp....: %s" % _versao_pacote("mcp"))
    print("pacote PyMuPDF: %s (opcional, tool ler_pdf)" % _versao_pacote("PyMuPDF"))
    print()

    cmd = cmd_extra or comando_padrao()
    print("--- handshake com o servidor ---")
    print("comando: %s" % " ".join(cmd))
    ok, explicacao, err = handshake(cmd)
    print("%s %s" % ("[OK]" if ok else "[FALHOU]", explicacao))
    if err.strip():
        print("stderr do servidor (ultimas linhas):")
        for linha in err.strip().splitlines()[-12:]:
            print("  | %s" % linha)
    print()

    print("--- o que o Claude Code sabe ---")
    print("$ claude mcp list")
    print(_rodar(["claude", "mcp", "list"]))
    print("$ claude mcp get lilo")
    print(_rodar(["claude", "mcp", "get", "lilo"]))
    print()

    try:
        from lilo import config
        log = Path(config.dir_dados()) / "logs" / "lilo.log"
        print("--- %s ---" % log)
        if log.exists():
            linhas = log.read_text(encoding="utf-8", errors="replace").splitlines()
            for linha in linhas[-15:]:
                print("  | %s" % linha)
        else:
            print("  (ainda nao existe)")
    except Exception as e:  # noqa: BLE001
        print("  (nao consegui ler o log: %s)" % e)

    print()
    print("Registrar/reparar a conexao:  .\\scripts\\conectar_claude_code.ps1")
    return 0 if ok else 1


def _extrair_cmd(args: list[str]) -> tuple[list[str], list[str] | None]:
    """`--cmd <programa> <args...>`: tudo depois de --cmd e a linha do servidor."""
    if "--cmd" not in args:
        return args, None
    i = args.index("--cmd")
    return args[:i], (args[i + 1:] or None)


def main(argv: list[str] | None = None) -> int:
    args, cmd = _extrair_cmd(list(argv if argv is not None else sys.argv[1:]))
    if "--handshake" in args:
        ok, explicacao, err = handshake(cmd)
        print("%s %s" % ("[OK]" if ok else "[FALHOU]", explicacao))
        if not ok and err.strip():
            for linha in err.strip().splitlines()[-12:]:
                print("  | %s" % linha)
        return 0 if ok else 1
    return relatorio(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
