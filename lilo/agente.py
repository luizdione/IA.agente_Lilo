"""O loop agentico do LILO v13 — o coracao que o legado nunca teve.

chat -> tool_calls -> executa (via choke-point) -> role:"tool" -> repete, ate
o modelo responder SEM tool_calls (= resposta final). Casamento tool_call/
resultado por ORDEM (a API nativa do Ollama nao garante id). Janela de
contexto gerida deterministicamente, sem LLM.
"""
from __future__ import annotations

from pathlib import Path

from lilo import config, contexto, tools
from lilo.cliente import ClienteOllama
from lilo.log import get_logger
from lilo.portao import Permissoes

log = get_logger("agente")

SYSTEM_BASE = """Voce e o LILO, um agente de IA que trabalha no TERMINAL do usuario, em portugues brasileiro.
Voce gerencia, escreve, conserta e cria projetos usando as tools: ler, listar, buscar, escrever, editar, shell.

Regras:
1. AJA com as tools, usando o mecanismo NATIVO de tool calls. NUNCA escreva a chamada como texto ou JSON na resposta — isso NAO executa nada. Uma resposta sem tool calls encerra a tarefa.
2. Antes de editar um arquivo, LEIA o trecho com `ler` e copie o texto EXATO para `editar`.
3. Depois de criar ou mudar codigo, RODE com `shell` (ex.: python arquivo.py, pytest) e conserte os erros que aparecerem.
4. Resultado "[ERRO] ..." = sua chamada tinha problema; corrija os argumentos e tente de novo.
5. Resultado "[NEGADO] ..." = o usuario recusou; NAO repita a mesma acao, proponha alternativa ou pergunte.
6. Caminhos sao relativos ao diretorio atual do usuario. Nao invente arquivos: confira com listar/buscar.
7. Ao terminar, responda curto: o que foi feito, o que foi verificado, e pendencias se houver.
8. Memoria persistente entre sessoes: memorizar(chave, valor) guarda fatos duraveis do usuario/projeto; lembrar(busca) recupera. Use com parcimonia.
9. A tool mcp acessa servidores MCP externos que o usuario configurou (mcp so com servidor lista as tools dele).

Exemplo de fluxo para "conserte o bug do script X": buscar/ler o arquivo -> editar o trecho -> shell p/ rodar/testar -> se falhar, ler o erro e editar de novo -> resposta final."""

MAX_ERROS_CONSECUTIVOS = 3
MAX_NUDGES = 2  # correcoes de "tool escrita como texto" por tarefa

NUDGE_TOOL_TEXTO = (
    "[SISTEMA] Sua resposta escreveu chamadas de tool como TEXTO/JSON — "
    "NADA foi executado. Refaca AGORA a mesma acao usando o mecanismo "
    "nativo de tool calls (nao escreva JSON na resposta).")


def _parece_tool_em_texto(content: str) -> bool:
    """Modo de falha classico de modelo pequeno: a 'resposta final' e o JSON
    de uma chamada de tool escrito como texto. NAO executamos nada disso
    (licao do legado: sem parser regex de pseudo-JSON) — apenas devolvemos
    uma correcao para o modelo refazer pelo canal nativo."""
    t = content.strip()
    if '"name"' not in t or '"arguments"' not in t:
        return False
    return any(
        ('"name": "%s"' % nome) in t or ('"name":"%s"' % nome) in t
        for nome in tools.TOOLS)


class UI:
    """Callbacks do terminal (o CLI implementa; os testes usam fakes)."""

    suporta_stream = False  # so a UI de terminal liga o streaming de tokens

    def confirmar(self, kind: str, preview: str) -> str:  # 's'|'n'|'t'
        return "n"

    def token(self, texto: str) -> None:
        """Pedaco de resposta chegando (streaming). Default: descarta."""

    def tool_inicio(self, nome: str, preview: str) -> None:
        pass

    def tool_fim(self, nome: str, resultado: str) -> None:
        pass

    def apos_iteracao(self, msgs: list[dict]) -> None:
        """Hook de persistencia (sessoes F4)."""


def montar_system(cwd: Path | None = None) -> str:
    bloco = contexto.bloco_projeto(cwd)
    return SYSTEM_BASE + ("\n\n" + bloco if bloco else "")


# --- janela de contexto (deterministica, sem LLM) ---------------------------
def _tok(msg: dict) -> int:
    """Estimativa: chars/3 (PT-BR e menos denso que ingles) + 8 de overhead."""
    total = len(str(msg.get("content") or "")) + len(str(msg.get("tool_calls") or ""))
    return total // 3 + 8


def ajustar_janela(msgs: list[dict]) -> list[dict]:
    """Poda quando o historico ameaca estourar num_ctx:
    1) substitui resultados de tool ANTIGOS (preserva os 4 ultimos);
    2) remove grupos antigos (assistant+suas tools / pares user-assistant).
    Nunca toca: system (indice 0) e o 1o pedido do usuario (indice 1)."""
    orcamento = config.num_ctx() - config.max_tokens() - 1024
    if sum(_tok(m) for m in msgs) <= orcamento:
        return msgs

    msgs = [dict(m) for m in msgs]  # copia rasa por mensagem

    # Passo 1: esvazia resultados de tool antigos
    idx_tools = [i for i, m in enumerate(msgs) if m.get("role") == "tool"]
    for i in idx_tools[:-4]:
        c = msgs[i].get("content") or ""
        if not c.startswith("[resultado antigo omitido"):
            msgs[i]["content"] = "[resultado antigo omitido — %d chars]" % len(c)
        if sum(_tok(m) for m in msgs) <= orcamento:
            return msgs

    # Passo 2: remove grupos antigos a partir do indice 2
    while sum(_tok(m) for m in msgs) > orcamento and len(msgs) > 3:
        i = 2
        if i >= len(msgs) - 1:  # nunca remove a ultima mensagem
            break
        grupo_fim = i + 1
        if msgs[i].get("role") == "assistant" and msgs[i].get("tool_calls"):
            while grupo_fim < len(msgs) and msgs[grupo_fim].get("role") == "tool":
                grupo_fim += 1
        if grupo_fim >= len(msgs):  # nao remover o rabo ativo da conversa
            break
        del msgs[i:grupo_fim]
    return msgs


# --- o loop -----------------------------------------------------------------
def executar_tarefa(tarefa: str, msgs: list[dict], perms: Permissoes,
                    cliente: ClienteOllama | None = None,
                    ui: UI | None = None,
                    modelo: str | None = None) -> tuple[str, list[dict]]:
    """Roda UMA tarefa dentro da conversa `msgs` (que ja contem o system).
    Retorna (resposta_final, msgs_atualizado). Pausa NO tool call para
    confirmacao (ui.confirmar) — nunca re-executa o pedido."""
    cliente = cliente or ClienteOllama()
    ui = ui or UI()

    msgs.append({"role": "user", "content": tarefa})
    erros_consec = 0
    nudges = 0

    for _ in range(config.max_iters()):
        msgs_envio = ajustar_janela(msgs)
        r = cliente.chat(msgs_envio, tools=tools.SCHEMAS, model=modelo,
                         on_token=ui.token if ui.suporta_stream else None)

        if not r["tool_calls"]:
            final = r["content"].strip() or "(o modelo nao produziu resposta)"
            if nudges < MAX_NUDGES and _parece_tool_em_texto(final):
                # tool escrita como texto: corrige e da outra chance
                nudges += 1
                log.warning("tool como texto detectada — nudge %d/%d",
                            nudges, MAX_NUDGES)
                msgs.append(r["message"])
                msgs.append({"role": "user", "content": NUDGE_TOOL_TEXTO})
                continue
            msgs.append({"role": "assistant", "content": final})
            ui.apos_iteracao(msgs)
            return final, msgs

        msgs.append(r["message"])  # turno assistant com os tool_calls, cru
        for tc in r["tool_calls"]:  # paralelos: sequencial, EM ORDEM
            nome, args = tc["name"], tc["arguments"]
            tool = tools.TOOLS.get(nome)
            preview = tool.preview(args) if tool else nome
            ui.tool_inicio(nome, preview)
            saida = tools.executar_tool(nome, args, perms, ui.confirmar)
            ui.tool_fim(nome, saida)
            msgs.append({"role": "tool", "tool_name": nome, "content": saida})
            erros_consec = erros_consec + 1 if saida.startswith("[ERRO]") else 0
        ui.apos_iteracao(msgs)

        if erros_consec >= MAX_ERROS_CONSECUTIVOS:
            aviso = ("[ABORTADO] %d erros de tool consecutivos. Revise a "
                     "tarefa ou o modelo (\\modelo)." % erros_consec)
            msgs.append({"role": "assistant", "content": aviso})
            return aviso, msgs

    aviso = "[LIMITE] %d iteracoes atingidas sem resposta final." % config.max_iters()
    msgs.append({"role": "assistant", "content": aviso})
    return aviso, msgs
