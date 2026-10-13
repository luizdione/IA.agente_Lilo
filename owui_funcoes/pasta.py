"""
title: Pasta de trabalho
author: LILO
version: 1.0
description: Botão da caixa de mensagem: ligado, o LILO trabalha na pasta definida em Controles > Valves (ou abre o seletor de pasta do Windows com pasta_escolher).
"""
import base64
from typing import Optional

from pydantic import BaseModel, Field

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 '
       '0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>')


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=15)

    class UserValves(BaseModel):
        caminho: str = Field(default="", description="Pasta de trabalho (ex.: C:\\GitHub\\LILO ou E:\\data\\projeto). "
                                                     "Vazio = o LILO abre o seletor de pasta do Windows.")

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True
        self.icon = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        valves = (__user__ or {}).get("valves")
        caminho = (getattr(valves, "caminho", "") or "").strip()
        if caminho:
            texto = ("Pasta de trabalho atual: %s. Trabalhe dentro dela: liste com pasta_listar (ou "
                     "tool_list_directory_post), procure com pasta_buscar, leia com ler_texto (ou "
                     "tool_read_file_post) e edite com tool_edit_block_post/tool_write_file_post quando "
                     "houver. Não invente caminhos fora dela." % caminho)
        else:
            texto = ("O dono quer trabalhar numa pasta mas ainda não a definiu: chame pasta_escolher para "
                     "abrir o seletor de pasta do Windows e use o caminho devolvido (ou peça que ele o "
                     "fixe em Controles > Valves > Pasta de trabalho).")
        msgs = body.setdefault("messages", [])
        if msgs and msgs[0].get("role") == "system":
            if texto not in str(msgs[0].get("content", "")):
                msgs[0]["content"] = str(msgs[0].get("content", "")) + "\n\n" + texto
        else:
            msgs.insert(0, {"role": "system", "content": texto})
        return body
