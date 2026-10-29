"""
title: Modo de agir
author: LILO
version: 1.0
description: Como o LILO age com as ferramentas: automático, manual (só leitura e pede confirmação), aceitar edições (lê e edita arquivos, sem shell), plano (não executa nada) ou ignorar permissões. Ajuste em Controles > Valves.
"""
# Filtro da Open WebUI (roda DENTRO do container). Restringe de verdade as tools que o modelo
# recebe, reescrevendo os tool_ids do pedido (sintaxe `server:mcp:<id>|f1,f2` da interface),
# instrui o modelo e liga a APROVACAO POR CHAMADA nativa da interface (0.11.1+: com
# ENABLE_TOOL_PERMISSIONS no compose, `params.tool_approval_mode = "ask"` faz a resposta pausar em
# cada tool com Allow/Deny; "full" executa direto). "manual" = tools so de leitura + ask.
import base64
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Botao no menu "Integracoes" da caixa (as valves do usuario so aparecem assim na 0.11): ligado =
# o modo escolhido na engrenagem; desligado = automatico.
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 4v5c0 5-3.5 8-8 9'
       '-4.5-1-8-4-8-9V7z"/><path d="M9 12l2 2 4-4"/></svg>')

LEITURA_ANALISE = ("estat_descrever,estat_normalidade,estat_teste_t,estat_mann_whitney,estat_anova,"
                   "estat_correlacao,estat_qui_quadrado,bio_parse_log,docx_ler")
LEITURA_DESKTOP = ("tool_read_file_post,tool_read_multiple_files_post,tool_list_directory_post,"
                   "tool_get_file_info_post,tool_start_search_post,tool_get_more_search_results_post,"
                   "tool_stop_search_post,tool_list_searches_post,tool_get_config_post")
EDICAO_DESKTOP = LEITURA_DESKTOP + (",tool_write_file_post,tool_edit_block_post,tool_create_directory_post,"
                                    "tool_move_file_post,tool_write_pdf_post")
LEITURA_CODIGO = "arquivo_ler,arquivo_buscar,arquivo_listar"
EDICAO_CODIGO = LEITURA_CODIGO + ",arquivo_escrever,arquivo_editar"     # sem executar_powershell
SEMPRE = ("server:mcp:conhecimento", "server:mcp:literatura", "server:mcp:pubmed", "server:mcp:biorxiv",
          "server:mcp:chembl", "server:mcp:ensaios", "server:mcp:opentargets")

# modo -> {id da conexao: None (todas as funcoes) | "f1,f2" (so estas)}; o que nao esta aqui sai.
PERMITIDO = {
    "manual": {**{s: None for s in SEMPRE}, "server:mcp:analise": LEITURA_ANALISE,
               "server:mcp:codigo": LEITURA_CODIGO, "server:desktop": LEITURA_DESKTOP},
    "aceitar_edicoes": {**{s: None for s in SEMPRE}, "server:mcp:analise": None,
                        "server:mcp:codigo": EDICAO_CODIGO, "server:desktop": EDICAO_DESKTOP},
    "plano": {},
}
# Aprovacao por chamada da interface (tool_approval_mode): "ask" pausa em cada tool com Allow/Deny.
APROVACAO = {"manual": "ask", "aceitar_edicoes": "full", "automatico": "full", "ignorar_permissoes": "full"}
INSTRUCAO = {
    "manual": "Modo manual: você só tem ferramentas de leitura e cada chamada pede aprovação do dono na "
              "tela. Antes de qualquer ação que altere, crie, mova ou execute algo, descreva exatamente o "
              "que faria e peça confirmação.",
    "aceitar_edicoes": "Modo aceitar edições: pode ler, criar e editar arquivos, mas não rodar comandos, "
                       "processos ou git. Para executar algo, descreva o comando e peça confirmação.",
    "plano": "Modo plano: não execute nada e não chame ferramentas. Entregue um plano numerado, com os "
             "arquivos e comandos que usaria, e pergunte se pode seguir.",
    "ignorar_permissoes": "Modo sem confirmações: execute o que for preciso para concluir a tarefa, "
                          "mostrando cada comando e saída.",
}


def restringir(tool_ids: list, modo: str) -> list:
    if modo not in PERMITIDO:
        return list(tool_ids or [])
    permitido = PERMITIDO[modo]
    saida = []
    for tid in tool_ids or []:
        base = str(tid).split("|", 1)[0]
        if base not in permitido:
            continue
        funcoes = permitido[base]
        # None = todas as funcoes: mantem o filtro que o preset ja trazia (ex.: sem resumir_arquivo)
        saida.append(str(tid) if funcoes is None else base + "|" + funcoes)
    return saida


def injetar_system(body: dict, texto: str) -> None:
    msgs = body.setdefault("messages", [])
    if msgs and msgs[0].get("role") == "system":
        if texto not in str(msgs[0].get("content", "")):
            msgs[0]["content"] = str(msgs[0].get("content", "")) + "\n\n" + texto
    else:
        msgs.insert(0, {"role": "system", "content": texto})


def aplicar_modo(body: dict, metadata: Optional[dict], modo: str) -> dict:
    # A interface le `metadata["params"]["tool_approval_mode"]` ao executar cada tool.
    aprovacao = APROVACAO.get(modo)
    if aprovacao:
        for alvo in (metadata, body):
            if isinstance(alvo, dict):
                params = alvo.get("params")
                if not isinstance(params, dict):
                    params = {}
                    alvo["params"] = params
                params["tool_approval_mode"] = aprovacao
    if modo == "automatico":
        return body
    for alvo in (metadata, body):
        if isinstance(alvo, dict) and alvo.get("tool_ids") is not None:
            alvo["tool_ids"] = restringir(alvo["tool_ids"], modo)
    if modo in ("manual", "aceitar_edicoes", "plano"):
        body.pop("terminal_id", None)    # terminal integrado (Open Terminal) e shell completo: so no automatico
    if modo in INSTRUCAO:
        injetar_system(body, INSTRUCAO[modo])
    return body


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=5)

    class UserValves(BaseModel):
        modo: Literal["automatico", "manual", "aceitar_edicoes", "plano", "ignorar_permissoes"] = Field(
            default="automatico",
            description="automático (tools do preset) · manual (só leitura, pede confirmação) · "
                        "aceitar_edicoes (lê e edita arquivos, sem shell) · plano (não executa) · "
                        "ignorar_permissoes (tudo, sem perguntar).",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True
        self.icon = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

    def inlet(self, body: dict, __user__: Optional[dict] = None, __metadata__: Optional[dict] = None) -> dict:
        valves = (__user__ or {}).get("valves")
        modo = getattr(valves, "modo", None) or "automatico"
        return aplicar_modo(body, __metadata__, modo)
