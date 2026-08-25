"""Smoke VIVO do LILO v13 — rode NA MAQUINA DO DONO, com o Ollama de pe.

    python scripts\\smoke_lilo.py

Etapas (para no primeiro FALHOU):
  1. Ollama acessivel + modelo presente (versao impressa — canario de upgrade)
  2. Aceite: LILO cria um script, RODA com shell e responde
  3. Aceite canonico: LILO ve um script com bug, conserta e prova rodando

Roda em sandbox temporaria com LILO_MODE=auto e allow-list apontada p/ ela —
nao toca nos seus projetos. E o teste de regressao contra updates do Ollama.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _falhou(msg: str) -> int:
    print("FALHOU — %s" % msg)
    return 1


def main() -> int:
    sandbox = Path(tempfile.mkdtemp(prefix="lilo_smoke_"))
    os.environ["LILO_MODE"] = "auto"
    os.environ["LILO_ALLOW"] = str(sandbox)
    os.chdir(sandbox)

    from lilo import config
    config.load_env(ROOT / ".env")
    os.environ["LILO_MODE"] = "auto"          # smoke sempre sem interacao
    os.environ["LILO_ALLOW"] = str(sandbox)   # e sempre na sandbox

    import requests

    from lilo import agente
    from lilo.cliente import ClienteOllama
    from lilo.portao import Permissoes

    host, modelo = config.ollama_host(), config.modelo()
    print("LILO smoke — host=%s modelo=%s sandbox=%s" % (host, modelo, sandbox))

    # --- Etapa 1: servidor + modelo ----------------------------------------
    try:
        ver = requests.get(host + "/api/version", timeout=3).json().get("version")
        tags = requests.get(host + "/api/tags", timeout=3).json()
    except requests.RequestException as e:
        return _falhou("Ollama inacessivel em %s (%s). Inicie o Ollama." % (host, e))
    nomes = [m.get("name", "") for m in tags.get("models", [])]
    print("[1/3] Ollama %s ON — %d modelos" % (ver, len(nomes)))
    if not any(n.startswith(modelo.split(":")[0]) for n in nomes):
        return _falhou("modelo %r ausente. Rode: ollama pull %s" % (modelo, modelo))

    cliente = ClienteOllama()
    msgs = [{"role": "system", "content": agente.montar_system(sandbox)}]
    perms = Permissoes(modo="auto")

    # --- Etapa 2: criar + rodar --------------------------------------------
    tarefa2 = ("Crie o arquivo ola.py que imprime exatamente 'ola do lilo', "
               "execute-o com a tool shell e, se a saida estiver certa, "
               "responda apenas: OK")
    final, msgs = agente.executar_tarefa(tarefa2, msgs, perms, cliente=cliente)
    criado = (sandbox / "ola.py").exists()
    rodou = any(m.get("role") == "tool" and "ola do lilo" in (m.get("content") or "")
                for m in msgs)
    if not (criado and rodou):
        return _falhou("etapa 2: criado=%s rodou=%s | resposta: %.200s"
                       % (criado, rodou, final))
    print("[2/3] criar+rodar OK — resposta: %.60s" % final)

    # --- Etapa 3: consertar sozinho (aceite canonico) ----------------------
    (sandbox / "buggy.py").write_text(
        'print("resultado: " + 21*2)\n', encoding="utf-8")  # TypeError
    tarefa3 = ("O arquivo buggy.py da erro ao rodar. Rode-o com shell, LEIA o "
               "erro, conserte com editar e rode de novo ate sair com exit=0. "
               "Ao final responda apenas: CONSERTADO")
    final, msgs = agente.executar_tarefa(tarefa3, msgs, perms, cliente=cliente)
    provas = [m for m in msgs if m.get("role") == "tool"
              and "[exit=0]" in (m.get("content") or "")
              and "resultado" in (m.get("content") or "")]
    if not provas:
        return _falhou("etapa 3: sem execucao final com exit=0 | resposta: %.200s"
                       % final)
    print("[3/3] consertou sozinho OK — resposta: %.60s" % final)

    print("\nPASSOU — o LILO v13 esta operacional nesta maquina.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
