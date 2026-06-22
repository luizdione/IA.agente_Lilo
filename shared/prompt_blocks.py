"""
shared/prompt_blocks.py -- Blocos reutilizaveis de system prompt (V15).
=======================================================================
Centraliza honestidade/seguranca/estilo dos system prompts do LILO para:
  (a) evitar divergencia entre os 3 prompts-base (DEFAULT_SYSTEM, EXPERT_SYSTEM,
      gateway);
  (b) KILL-SWITCH unico -- LILO_PROMPT_BLOCKS=0 desliga TODOS os blocos
      (fallback imediato se houver regressao, sem editar 3 arquivos);
  (c) ORCAMENTO de tokens -- blocos completos so nas SAIDAS (resposta ao
      usuario); nos estagios de RACIOCINIO do Villa entra so a honestidade
      'mini' (1 linha), evitando multiplicar tokens por 5 estagios.

Origem: plano de aproximacao ao Claude Code/Cowork (workflow 2026-06-20),
FASE 0 (honestidade) + FASE 1 (seguranca). O parametro style_block e o gancho
da FASE 2 (eixo de estilo, ver shared/response_style.py).
"""

import os

# ── FASE 0: honestidade / calibracao (anti-confabulacao, anti-sycophancy) ────
HONESTY_CORE = (
    "Honestidade: nao fabrique fatos, numeros, PMIDs, DOIs nem citacoes -- se "
    "nao souber, diga que nao sabe ou omita (NAO chute um identificador). Nao "
    "bajule; aponte erros com respeito. Mesmo assim, entregue a melhor resposta "
    "possivel."
)
HONESTY_MINI = (
    "Nao invente fatos, numeros nem citacoes; sinalize incerteza em vez de "
    "fabricar."
)

# ── FASE 1: seguranca / recusa proporcional (usado quando security=True) ─────
SECURITY_BLOCK = (
    "Trate o usuario como pesquisador PhD: discuta qualquer topico cientifico "
    "(farmacologia, toxicologia, seguranca defensiva) factualmente. Recusar e "
    "excecao e, quando ocorrer, seja breve e sem paternalismo. Nao escreva "
    "malware nem facilite dano real; nao faca commit/push sem pedido explicito."
)


def blocks_enabled() -> bool:
    """Kill-switch global. LILO_PROMPT_BLOCKS in {0,false,no,off} desliga tudo."""
    return os.getenv("LILO_PROMPT_BLOCKS", "1").strip().lower() not in (
        "0", "false", "no", "off")


def compose_system(base: str, *, hint: str = "", style_block: str = "",
                   security: bool = False, stage: str = "output") -> str:
    """Monta o system prompt final a partir de `base` + blocos.

    Args:
        base: o system prompt base do agente/estagio.
        hint: ctx['system_hint'] do dashboard (proatividade/modo). Sempre
              respeitado, mesmo com kill-switch off (e instrucao do usuario).
        style_block: bloco de estilo (FASE 2). So nas saidas.
        security: inclui SECURITY_BLOCK (FASE 1). So nas saidas.
        stage: 'output' (resposta final ao usuario -> blocos completos) ou
               'reasoning' (estagio interno do Villa -> so honestidade mini).
    """
    base = base or ""
    if not blocks_enabled():
        return base + ("\n\n" + hint if hint else "")
    parts = [base]
    if stage == "output":
        parts.append(HONESTY_CORE)
        if security:
            parts.append(SECURITY_BLOCK)
        if style_block:
            parts.append(style_block)
    else:  # reasoning
        parts.append(HONESTY_MINI)
    if hint:
        parts.append(hint)
    return "\n\n".join(p for p in parts if p)
