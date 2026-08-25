"""Smoke VIVO do LILO v13 — com AUTO-DESCOBERTA de modelo.

    python scripts\\smoke_lilo.py

Fluxo:
  1. Ollama acessivel; lista os modelos instalados e suas capabilities.
  2. Monta a fila de candidatos: o LILO_MODEL configurado primeiro, depois os
     modelos instalados com capability 'tools' (sem downloads novos).
  3. Para cada candidato roda os ACEITES em sandbox %TEMP% fresca, modo auto:
       a) criar um script e executa-lo com a tool shell;
       b) canonico: ver um script com bug, consertar e provar com exit=0.
  4. O primeiro que passar e GRAVADO no .env (LILO_MODEL=...) — pronto.

E o teste de regressao contra updates do Ollama; nao toca nos seus projetos.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Familias preferidas para desempate (indice menor = testa antes)
PREFERENCIA = ("qwen3", "qwen2.5-coder", "llama3.1", "qwen2.5", "mistral",
               "llama3.2", "gpt-oss")
MAX_CANDIDATOS = 3


def _rank(nome: str) -> int:
    for i, p in enumerate(PREFERENCIA):
        if nome.startswith(p):
            return i
    return len(PREFERENCIA)


def _capabilities(requests, host: str, nome: str) -> list:
    try:
        r = requests.post(host + "/api/show", json={"model": nome},
                          timeout=5).json()
        return r.get("capabilities") or []
    except Exception:  # noqa: BLE001 — API antiga sem /api/show detalhado
        return []


def _sandbox_nova() -> Path:
    sb = Path(tempfile.mkdtemp(prefix="lilo_smoke_"))
    os.environ["LILO_ALLOW"] = str(sb)
    os.chdir(sb)
    return sb


def _testar_modelo(modelo: str) -> tuple[bool, str]:
    """Roda os 2 aceites com `modelo` numa sandbox fresca. (ok, motivo)."""
    from lilo import agente
    from lilo.cliente import ClienteOllama
    from lilo.portao import Permissoes

    sb = _sandbox_nova()
    cliente = ClienteOllama()
    msgs = [{"role": "system", "content": agente.montar_system(sb)}]
    perms = Permissoes(modo="auto")

    # Aceite A: criar + rodar
    t1 = ("Crie o arquivo ola.py que imprime exatamente 'ola do lilo', "
          "execute-o com a tool shell e, se a saida estiver certa, "
          "responda apenas: OK")
    final, msgs = agente.executar_tarefa(t1, msgs, perms, cliente=cliente,
                                         modelo=modelo)
    criado = (sb / "ola.py").exists()
    rodou = any(m.get("role") == "tool" and "ola do lilo" in (m.get("content") or "")
                for m in msgs)
    if not (criado and rodou):
        extra = ""
        if '"name"' in final and '"arguments"' in final:
            extra = " [tool escrita como TEXTO mesmo apos nudges]"
        return False, "criar+rodar: criado=%s rodou=%s%s | %.160s" % (
            criado, rodou, extra, final)

    # Aceite B (canonico): consertar sozinho
    (sb / "buggy.py").write_text('print("resultado: " + 21*2)\n',
                                 encoding="utf-8")  # TypeError proposital
    t2 = ("O arquivo buggy.py da erro ao rodar. Rode-o com shell, LEIA o "
          "erro, conserte com a tool editar e rode de novo ate sair com "
          "exit=0. Ao final responda apenas: CONSERTADO")
    final, msgs = agente.executar_tarefa(t2, msgs, perms, cliente=cliente,
                                         modelo=modelo)
    provas = [m for m in msgs if m.get("role") == "tool"
              and "[exit=0]" in (m.get("content") or "")
              and "resultado" in (m.get("content") or "")]
    if not provas:
        return False, "consertar: sem execucao final exit=0 | %.160s" % final
    return True, "ok"


def _gravar_env_modelo(modelo: str) -> None:
    env = ROOT / ".env"
    linhas = []
    if env.exists():
        linhas = [l for l in env.read_text(encoding="utf-8").splitlines()
                  if not l.strip().startswith("LILO_MODEL=")]
    linhas.append("LILO_MODEL=" + modelo)
    env.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> int:
    os.environ["LILO_MODE"] = "auto"  # smoke nunca pede confirmacao

    from lilo import config
    config.load_env(ROOT / ".env")
    os.environ["LILO_MODE"] = "auto"

    import requests

    host = config.ollama_host()
    configurado = config.modelo()
    print("LILO smoke — host=%s | configurado=%s" % (host, configurado))

    # --- [1] servidor + inventario -----------------------------------------
    try:
        ver = requests.get(host + "/api/version", timeout=3).json().get("version")
        tags = requests.get(host + "/api/tags", timeout=3).json()
    except requests.RequestException as e:
        print("FALHOU — Ollama inacessivel em %s (%s). Inicie o Ollama." % (host, e))
        return 1
    nomes = [m.get("name", "") for m in tags.get("models", [])]
    print("[1] Ollama %s ON — %d modelos instalados" % (ver, len(nomes)))

    com_tools = []
    for n in nomes:
        caps = _capabilities(requests, host, n)
        if "tools" in caps:
            com_tools.append(n)
    if com_tools:
        print("    com capability tools: %s" % ", ".join(sorted(com_tools, key=_rank)))

    # --- [2] fila de candidatos --------------------------------------------
    candidatos: list[str] = []
    base_cfg = configurado.split(":")[0]
    if any(n.startswith(base_cfg) for n in nomes):
        candidatos.append(configurado)
    else:
        print("    aviso: %s nao esta instalado (ollama pull %s) — testando "
              "os instalados" % (configurado, configurado))
    for n in sorted(com_tools, key=_rank):
        if n not in candidatos and len(candidatos) < MAX_CANDIDATOS:
            candidatos.append(n)
    if not candidatos:
        print("FALHOU — nenhum modelo com capability 'tools' instalado.\n"
              "Sugestao: ollama pull qwen3:14b  (ou llama3.1:8b)")
        return 1

    # --- [3] testa em ordem ------------------------------------------------
    for i, modelo in enumerate(candidatos, 1):
        print("[2] candidato %d/%d: %s ..." % (i, len(candidatos), modelo))
        try:
            ok, motivo = _testar_modelo(modelo)
        except Exception as e:  # noqa: BLE001 — segue p/ o proximo candidato
            ok, motivo = False, "%s: %s" % (type(e).__name__, e)
        if ok:
            _gravar_env_modelo(modelo)
            print("[3] aceites OK com %s — gravado no .env (LILO_MODEL)" % modelo)
            print("\nPASSOU — o LILO v13 esta operacional com %s." % modelo)
            return 0
        print("    falhou: %s" % motivo)

    print("\nFALHOU — nenhum candidato passou nos aceites.\n"
          "Sugestao: ollama pull qwen3:14b   e rode de novo\n"
          "(qwen3 tem o template de tools mais robusto da familia)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
