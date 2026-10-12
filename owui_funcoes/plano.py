"""
title: Plano
author: LILO
version: 1.0
description: Botão da caixa de mensagem: ligado, o LILO só planeja (nenhuma ferramenta é chamada) nesta conversa.
"""
import base64
from typing import Optional

from pydantic import BaseModel, Field

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" '
       'rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>')
TEXTO = ("Modo plano: não execute nada e não chame ferramentas. Entregue um plano numerado, com os "
         "arquivos e comandos que usaria, e pergunte se pode seguir.")


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=20, description="Roda por último: vence o Modo de agir.")

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True
        self.icon = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

    def inlet(self, body: dict, __metadata__: Optional[dict] = None) -> dict:
        for alvo in (__metadata__, body):
            if isinstance(alvo, dict) and alvo.get("tool_ids") is not None:
                alvo["tool_ids"] = []
        msgs = body.setdefault("messages", [])
        if msgs and msgs[0].get("role") == "system":
            if TEXTO not in str(msgs[0].get("content", "")):
                msgs[0]["content"] = str(msgs[0].get("content", "")) + "\n\n" + TEXTO
        else:
            msgs.insert(0, {"role": "system", "content": TEXTO})
        return body
