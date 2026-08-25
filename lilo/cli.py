"""CLI do LILO v13 — one-shot (`lilo "tarefa"`) e REPL interativo.

A confirmacao de permissao acontece NO PONTO da acao (o loop pausa na tool
e continua com o resultado ou com [NEGADO]) — nunca ha replay do pedido.
Modo plan: leituras executam, acoes acumulam; aprovar continua A MESMA
conversa com "Plano aprovado. Execute-o."
"""
from __future__ import annotations

import sys
from pathlib import Path

from lilo import __version__, agente, config
from lilo.cliente import ClienteOllama
from lilo.portao import MODOS, Permissoes

AJUDA = """Comandos do REPL:
  \\modo <plan|ask|accept_edits|auto>   troca o modo de permissao
  \\modelo <nome|fast>                  troca o modelo (fast = LILO_MODEL_FAST)
  \\plano                               mostra/aprova o plano acumulado (modo plan)
  \\nova                                zera a conversa (novo chat)
  \\ajuda                               esta ajuda
  \\sair                                encerra
Qualquer outro texto = tarefa para o agente. Ctrl+C cancela a tarefa atual."""


class UITerminal(agente.UI):
    """Callbacks de terminal: imprime tools e pergunta s/n/t no stdin."""

    def __init__(self, sessao: "Sessao | None" = None):
        self.sessao = sessao

    def apos_iteracao(self, msgs: list[dict]) -> None:
        if self.sessao is not None:
            self.sessao.persistir(msgs)

    def confirmar(self, kind: str, preview: str) -> str:
        print("\n┌─ CONFIRMACAO (%s) " % kind + "─" * max(0, 40 - len(kind)))
        for linha in preview.splitlines()[:14]:
            print("│ " + linha)
        print("└" + "─" * 55)
        while True:
            try:
                r = input("Executar? [s]im  [n]ao  [t]=sempre nesta sessao: ")
            except (EOFError, KeyboardInterrupt):
                print()
                return "n"
            r = r.strip().lower()[:1]
            if r in ("s", "n", "t"):
                return r

    def tool_inicio(self, nome: str, preview: str) -> None:
        print("  → %s" % preview.splitlines()[0][:100])

    def tool_fim(self, nome: str, resultado: str) -> None:
        primeira = (resultado.splitlines() or [""])[0]
        if resultado.startswith(("[ERRO]", "[NEGADO]", "[BLOQUEADO]")):
            print("    %s" % primeira[:120])


class Sessao:
    """Estado de uma conversa do CLI (mensagens + permissoes + modelo)."""

    def __init__(self):
        self.perms = Permissoes(modo=config.modo_inicial())
        self.modelo: str | None = None  # None = config.modelo()
        self.chat_id: str | None = None  # criado no 1o persistir
        self.msgs: list[dict] = [
            {"role": "system", "content": agente.montar_system(Path.cwd())}]

    def persistir(self, msgs: list[dict]) -> None:
        """Grava o transcript a cada iteracao — nunca derruba o turno."""
        try:
            from lilo import sessoes
            if self.chat_id is None:
                self.chat_id = sessoes.nova_sessao(str(Path.cwd()))
            sessoes.gravar(self.chat_id, msgs)
        except Exception:  # noqa: BLE001 — persistencia e best-effort
            pass

    def rodar(self, tarefa: str, ui: agente.UI, cliente: ClienteOllama) -> str:
        resposta, self.msgs = agente.executar_tarefa(
            tarefa, self.msgs, self.perms, cliente=cliente, ui=ui,
            modelo=self.modelo)
        return resposta


def _comando(linha: str, sessao: Sessao, ui: agente.UI,
             cliente: ClienteOllama) -> bool:
    """Trata \\comandos. Retorna True se a linha era um comando."""
    if not linha.startswith("\\"):
        return False
    partes = linha[1:].split(None, 1)
    cmd = partes[0].lower() if partes else ""
    arg = partes[1].strip() if len(partes) > 1 else ""

    if cmd == "sair":
        raise SystemExit(0)
    if cmd == "ajuda":
        print(AJUDA)
    elif cmd == "modo":
        if sessao.perms.trocar_modo(arg):
            print("modo: %s" % arg)
        else:
            print("modos validos: %s" % ", ".join(MODOS))
    elif cmd == "modelo":
        if arg == "fast":
            sessao.modelo = config.modelo_fast()
        elif arg:
            sessao.modelo = arg
        print("modelo: %s" % (sessao.modelo or config.modelo()))
    elif cmd == "nova":
        sessao.__init__()
        print("nova conversa (modo %s)" % sessao.perms.modo)
    elif cmd == "plano":
        plano = sessao.perms.plano
        if not plano:
            print("(plano vazio — use \\modo plan e peca uma tarefa)")
            return True
        print("Plano acumulado (%d acoes):" % len(plano))
        for i, (kind, prev) in enumerate(plano, 1):
            print("  %d. [%s] %s" % (i, kind, prev.splitlines()[0][:100]))
        try:
            ok = input("Aprovar e executar? [s/N]: ").strip().lower()[:1]
        except (EOFError, KeyboardInterrupt):
            ok = "n"
        if ok == "s":
            sessao.perms.plano.clear()
            sessao.perms.trocar_modo("accept_edits")
            print("modo: accept_edits — executando o plano na MESMA conversa...")
            resposta = sessao.rodar(
                "Plano aprovado pelo usuario. Execute-o agora.", ui, cliente)
            print("\n" + resposta)
    else:
        print("comando desconhecido: \\%s (\\ajuda lista)" % cmd)
    return True


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":  # cmd.exe com acentos
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass

    config.load_env()
    args = list(argv or [])
    continuar = "-c" in args
    if continuar:
        args.remove("-c")
    tarefa = " ".join(args).strip()

    cliente = ClienteOllama()
    sessao = Sessao()
    ui = UITerminal(sessao)
    if continuar:
        try:
            from lilo import sessoes
            cid = sessoes.ultima_sessao()
            if cid:
                sessao.chat_id = cid
                sessao.msgs = sessoes.carregar(cid)
                print("(sessao anterior retomada — %d mensagens)"
                      % len(sessao.msgs))
        except Exception:  # noqa: BLE001 — retomada e best-effort
            pass

    if tarefa:  # one-shot
        try:
            print(sessao.rodar(tarefa, ui, cliente))
            return 0
        except KeyboardInterrupt:
            print("\n[cancelado]")
            return 130
        except Exception as e:  # noqa: BLE001 — erro final vira mensagem util
            print("[ERRO] %s: %s" % (type(e).__name__, e))
            if not cliente.ping():
                print("O Ollama parece OFFLINE em %s — inicie-o e tente de novo."
                      % config.ollama_host())
            return 1

    # REPL
    print("LILO v%s — modelo %s · modo %s · Ollama %s" % (
        __version__, config.modelo(), sessao.perms.modo,
        "ON" if cliente.ping() else "OFF (inicie o Ollama!)"))
    print("Digite uma tarefa, \\ajuda para comandos, \\sair para encerrar.")
    while True:
        try:
            linha = input("\nlilo> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not linha:
            continue
        if _comando(linha, sessao, ui, cliente):
            continue
        try:
            print("\n" + sessao.rodar(linha, ui, cliente))
            if sessao.perms.modo == "plan" and sessao.perms.plano:
                print("(%d acoes anotadas — \\plano para revisar e aprovar)"
                      % len(sessao.perms.plano))
        except KeyboardInterrupt:
            print("\n[cancelado pelo usuario — a conversa continua]")
        except Exception as e:  # noqa: BLE001 — REPL nunca morre por erro de turno
            print("\n[ERRO] %s: %s" % (type(e).__name__, e))
