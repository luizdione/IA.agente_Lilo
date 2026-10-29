"""
title: Escolha Automática de Parâmetros
author: LILO
version: 1.0
description: Profundidade de raciocínio (baixo, médio, alto, extra, máximo, ultracode) que escolhe de uma vez os parâmetros do modelo. Ajuste em Controles > Valves.
"""
# Filtro da Open WebUI (roda DENTRO do container; sem imports do repo). O nivel vira
# temperature/top_p/max_tokens e, para modelos que pensam, `think`; no Claude vira
# `reasoning_effort`. Nunca mexe em num_ctx nem em opcao de runner (recarregaria o modelo).
import base64
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Na Open WebUI 0.11 as valves do usuario so aparecem para filtros COM botao (menu "Integracoes"
# da caixa de mensagem, engrenagem ao lado): por isso este filtro e um botao. Desligado = padrao
# "medio" da interface; ligado = o nivel escolhido na engrenagem.
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18h3M4 12h8M4 6h13"/>'
       '<circle cx="17" cy="18" r="2"/><circle cx="7" cy="12" r="2"/><circle cx="20" cy="6" r="2"/></svg>')

NIVEIS = {
    "baixo": dict(think=False, temperature=0.2, top_p=0.8, max_tokens=512, esforco="low", extra=""),
    "medio": dict(think=False, temperature=0.5, top_p=0.9, max_tokens=1536, esforco="medium", extra=""),
    "alto": dict(think=True, temperature=0.6, top_p=0.9, max_tokens=3072, esforco="high", extra=""),
    "extra": dict(think=True, temperature=0.6, top_p=0.95, max_tokens=4096, esforco="high", extra=""),
    "maximo": dict(think=True, temperature=0.6, top_p=0.95, max_tokens=6144, esforco="high",
                   extra="Antes de responder, revise a resposta inteira e corrija o que estiver errado."),
    "ultracode": dict(think=True, temperature=0.3, top_p=0.9, max_tokens=6144, esforco="high",
                      extra="Modo código: planeje em etapas, implemente, teste com as ferramentas disponíveis "
                            "e revise antes de entregar; mostre o código e a saída dos testes."),
}


def injetar_system(body: dict, texto: str) -> None:
    msgs = body.setdefault("messages", [])
    if msgs and msgs[0].get("role") == "system":
        if texto not in str(msgs[0].get("content", "")):
            msgs[0]["content"] = str(msgs[0].get("content", "")) + "\n\n" + texto
    else:
        msgs.insert(0, {"role": "system", "content": texto})


AGENTE_MIN_TOKENS = 4096   # com tools, um arquivo_escrever de 200 linhas nao pode ser cortado


def _com_tools(body: dict, metadata: Optional[dict]) -> bool:
    for alvo in (metadata, body):
        if isinstance(alvo, dict) and alvo.get("tool_ids"):
            return True
    return False


def aplicar_nivel(body: dict, nivel: str, modelo: Optional[dict], metadata: Optional[dict] = None) -> dict:
    p = NIVEIS.get(nivel, NIVEIS["medio"])
    dono = str((modelo or {}).get("owned_by", "")).lower()
    # Niveis rapidos (baixo/medio) limitam a resposta; num preset que AGE o teto sobe para o
    # modelo conseguir gravar um arquivo inteiro numa chamada (o ganho de velocidade vem de nao
    # pensar, nao do teto de tokens).
    max_tokens = max(p["max_tokens"], AGENTE_MIN_TOKENS) if _com_tools(body, metadata) else p["max_tokens"]
    if dono == "openai":
        # Claude pela API compativel com OpenAI: a Anthropic recusa temperature+top_p juntos (e
        # temperature != 1 com raciocinio ligado) -> so o esforco de raciocinio e o teto de saida.
        body.pop("temperature", None)
        body.pop("top_p", None)
        body["max_tokens"] = max_tokens
        body["reasoning_effort"] = p["esforco"]
    else:
        # Ollama: a interface ja montou `options` a partir dos params do modelo; os valores de
        # amostragem vivem ai (nao no nivel de cima). `think` e campo proprio do /api/chat.
        opts = body.setdefault("options", {}) or {}
        # DEFAULT_MODEL_PARAMS (think:false) chega em options e e copiado para o campo `think` do
        # pedido depois dos filtros: por isso o valor entra nos dois lugares.
        # gpt-oss nao aceita think:false (raciocina sempre): recebe o nivel low/medium/high.
        alvo = str(body.get("model") or "") + " " + str((modelo or {}).get("id") or "")
        think = p["think"]
        if "oss" in alvo.lower():
            think = {"low": "low", "medium": "low", "high": "high"}[p["esforco"]]
        opts.update({"temperature": p["temperature"], "top_p": p["top_p"], "num_predict": max_tokens,
                     "think": think})
        body["options"] = opts
        body["think"] = think               # lilo = qwen3, gemma4 pensam; qwen2.5 ignora
    if p["extra"]:
        injetar_system(body, p["extra"])
    return body


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Ordem entre filtros (menor roda antes).")

    class UserValves(BaseModel):
        nivel: Literal["baixo", "medio", "alto", "extra", "maximo", "ultracode"] = Field(
            default="medio",
            description="Profundidade: baixo (rápido, sem pensar) · médio (padrão) · alto (pensa) · "
                        "extra · máximo (pensa e revisa) · ultracode (código em etapas com testes).",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True
        self.icon = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

    def inlet(self, body: dict, __user__: Optional[dict] = None, __model__: Optional[dict] = None,
              __metadata__: Optional[dict] = None) -> dict:
        valves = (__user__ or {}).get("valves")
        nivel = getattr(valves, "nivel", None) or "medio"
        return aplicar_nivel(body, nivel, __model__, __metadata__)
