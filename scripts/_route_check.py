#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Verificador transitorio do roteamento pos-correcao V10.3 (pode apagar).
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
from agents.villa_lobos.agent import VillaLobosAgent

PHRASES = {
    "conhecimentos_gerais": "Quais são os pilares de uma dieta equilibrada e como afetam o metabolismo energético?",
    "historia": "Explique as principais causas econômicas e sociais da Revolução Francesa.",
    "geografia": "Descreva a formação e a importância das bacias hidrográficas do Brasil.",
    "quimica": "Detalhe o mecanismo da esterificação de Fischer, incluindo catálise ácida e equilíbrio.",
    "biologia": "Como funciona a replicação do DNA em eucariotos? Cite enzimas e etapas.",
    "fisica": "Explique o princípio da incerteza de Heisenberg e suas implicações físicas.",
    "matematica": "Enuncie e demonstre o teorema fundamental do cálculo.",
    "agropecuaria": "Quais fatores edafoclimáticos afetam a produtividade da soja no cerrado brasileiro?",
    "veterinaria": "Quais são os sinais clínicos, o diagnóstico e o manejo da cinomose em cães?",
    "_controle_trivial": "o que e PCR",
}
ag = VillaLobosAgent()
print("%-22s %-10s %-7s %s" % ("dominio", "complex", "skip", "iters"))
for dom, q in PHRASES.items():
    d = ag._orchestrate_decision(q, use_cache=False)
    print("%-22s %-10s %-7s %s" % (dom, d.get("complexity"),
          str(d.get("skip_to_reporter")), d.get("iterations")))
