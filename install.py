#!/usr/bin/env python3
"""
install.py -- Instalador multiplataforma do LILO (Windows / Linux / macOS).

Faz, num passo so:
  1. Verifica a versao do Python (>= 3.10).
  2. Instala as dependencias (pip install -r requirements.txt).
  3. Cria o .env a partir do .env.example (se ainda nao existir).
  4. Configura o VINCULO COM O CLAUDE: pergunta (opcional) a sua ANTHROPIC_API_KEY
     e grava no .env LOCAL (nunca versionado).
  5. Verifica o Ollama e (opcional) baixa o modelo de chat base.
  6. Imprime como subir o dashboard.

Uso:
  python install.py                 # interativo (recomendado)
  python install.py --no-input      # nao pergunta nada (CI / automacao)
  python install.py --venv          # cria e usa um .venv dedicado
  python install.py --model gemma3:12b --no-pull   # nao baixa modelo

Nao requer nada alem da biblioteca padrao do Python para rodar.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQ = ROOT / "requirements.txt"
ENV = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
DEFAULT_MODEL = "gemma3:12b"
MIN_PY = (3, 10)

_C = {"ok": "\033[92m", "warn": "\033[93m", "err": "\033[91m", "b": "\033[1m", "z": "\033[0m"}
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    _C = {k: "" for k in _C}  # cmd.exe antigo sem ANSI


def say(msg, kind="b"):
    print(f"{_C.get(kind, '')}{msg}{_C['z']}")


def run(cmd, **kw):
    say(">> " + " ".join(str(c) for c in cmd), "warn")
    return subprocess.run(cmd, **kw)


# ---------------------------------------------------------------------------
def check_python():
    if sys.version_info < MIN_PY:
        say("Python %d.%d+ necessario (voce tem %d.%d)."
            % (*MIN_PY, sys.version_info.major, sys.version_info.minor), "err")
        sys.exit(1)
    say("[OK] Python %d.%d.%d"
        % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro), "ok")


def make_venv() -> str:
    venv_dir = ROOT / ".venv"
    if not venv_dir.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])
    py = (venv_dir / ("Scripts" if os.name == "nt" else "bin")
          / ("python.exe" if os.name == "nt" else "python"))
    say("[OK] venv em %s" % venv_dir, "ok")
    return str(py)


def pip_install(py: str):
    if not REQ.exists():
        say("requirements.txt nao encontrado em %s" % ROOT, "err")
        sys.exit(1)
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    r = run([py, "-m", "pip", "install", "-r", str(REQ)])
    if r.returncode != 0:
        say("[ERRO] pip install falhou. Verifique a saida acima.", "err")
        sys.exit(r.returncode)
    say("[OK] Dependencias instaladas.", "ok")


def ensure_env():
    if ENV.exists():
        say("[OK] .env ja existe (nao sobrescrevo).", "ok")
        return
    if ENV_EXAMPLE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV)
        say("[OK] .env criado a partir de .env.example.", "ok")
    else:
        ENV.write_text("# LILO .env\n", encoding="utf-8")
        say("[OK] .env criado (vazio).", "ok")


def set_env_var(key: str, value: str):
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    out, found = [], False
    for ln in lines:
        if ln.strip().startswith(key + "=") and not ln.strip().startswith("#"):
            out.append("%s=%s" % (key, value))
            found = True
        else:
            out.append(ln)
    if not found:
        out.append("%s=%s" % (key, value))
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")


def configure_claude(no_input: bool):
    """Vinculo com o Claude: grava a ANTHROPIC_API_KEY no .env local (opcional)."""
    if no_input:
        return
    say("\n--- Vinculo com o Claude (opcional) ---")
    print("Sem a chave, o LILO roda 100% local (Ollama). A chave habilita o")
    print("fallback Claude para tarefas complexas, respeitando LILO_DAILY_BUDGET.")
    print("A chave e' gravada SO no seu .env local (nunca versionada).")
    try:
        import getpass
        key = getpass.getpass("ANTHROPIC_API_KEY (Enter p/ pular): ").strip()
    except Exception:
        key = input("ANTHROPIC_API_KEY (Enter p/ pular): ").strip()
    if key:
        set_env_var("ANTHROPIC_API_KEY", key)
        say("[OK] Chave gravada no .env.", "ok")
    else:
        say("[--] Sem chave: modo 100% local.", "warn")


def _ollama_running() -> bool:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def setup_ollama(model: str, no_pull: bool, no_input: bool):
    say("\n--- Ollama ---")
    if shutil.which("ollama") is None:
        say("[!] Ollama nao encontrado no PATH. Instale em https://ollama.com/download",
            "warn")
        say("    (o LILO precisa do Ollama para os modelos locais).", "warn")
        return
    say("[OK] Ollama instalado.", "ok")
    if not _ollama_running():
        say("[!] Servico Ollama parece parado. Inicie com: ollama serve", "warn")
    if no_pull:
        return
    do = True
    if not no_input:
        do = (input("Baixar o modelo base '%s' agora (varios GB)? [S/n]: " % model)
              .strip().lower() not in ("n", "nao", "no"))
    if do:
        run(["ollama", "pull", model])
        say("[OK] Modelo %s pronto." % model, "ok")


def main() -> int:
    ap = argparse.ArgumentParser(description="Instalador do LILO.")
    ap.add_argument("--no-input", action="store_true", help="Nao faz perguntas.")
    ap.add_argument("--venv", action="store_true", help="Cria/usa um .venv dedicado.")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama base.")
    ap.add_argument("--no-pull", action="store_true", help="Nao baixa o modelo Ollama.")
    args = ap.parse_args()

    say("=" * 60)
    say("  Instalador do LILO -- Local Intelligent LLM Orchestrator")
    say("=" * 60)

    check_python()
    py = make_venv() if args.venv else sys.executable
    pip_install(py)
    ensure_env()
    configure_claude(args.no_input)
    setup_ollama(args.model, args.no_pull, args.no_input)

    say("\n" + "=" * 60)
    say("  LILO instalado!", "ok")
    say("=" * 60)
    run_py = ".venv path" if args.venv else "python"
    print("\nSuba o dashboard:")
    if args.venv and os.name == "nt":
        print("  .venv\\Scripts\\streamlit run dashboard.py --server.port 8100")
    elif args.venv:
        print("  .venv/bin/streamlit run dashboard.py --server.port 8100")
    else:
        print("  streamlit run dashboard.py --server.port 8100")
    print("  -> http://localhost:8100")
    print("\nCLI:   python lilo.py health")
    print("Docs:  README.md  |  Licenca: LICENSE (uso cientifico, c/ autorizacao)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
