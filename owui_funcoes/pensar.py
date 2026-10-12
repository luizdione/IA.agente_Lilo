"""
title: Pensar fundo
author: LILO
version: 1.0
description: Botão da caixa de mensagem: ligado, o modelo pensa antes de responder (nível "alto" da Escolha Automática de Parâmetros) só nesta conversa.
"""
import base64
from typing import Optional

from pydantic import BaseModel, Field

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a4 4 0 0 0-4 4v1a3 3 0 '
       '0 0-2 5 3 3 0 0 0 1 5.8V19a2 2 0 0 0 4 0v-1"/><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 2 5 3 3 0 0 1 '
       '-1 5.8V19a2 2 0 0 1-4 0v-1"/><path d="M12 3v15"/></svg>')
ALTO = dict(temperature=0.6, top_p=0.9, max_tokens=3072)


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=10, description="Roda depois da Escolha Automática (sobrepõe o nível).")

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True
        self.icon = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

    def inlet(self, body: dict, __model__: Optional[dict] = None) -> dict:
        if str((__model__ or {}).get("owned_by", "")).lower() == "openai":
            body.pop("temperature", None)       # a Anthropic recusa temperature/top_p com raciocinio
            body.pop("top_p", None)
            body["max_tokens"] = ALTO["max_tokens"]
            body["reasoning_effort"] = "high"
        else:
            opts = body.setdefault("options", {}) or {}
            opts.update({"temperature": ALTO["temperature"], "top_p": ALTO["top_p"], "num_predict": ALTO["max_tokens"],
                         "think": True})      # tambem em options: e de la que a interface copia o `think`
            body["options"] = opts
            body["think"] = True
        return body
