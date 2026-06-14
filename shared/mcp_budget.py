"""
shared/mcp_budget.py -- Guarda de orcamento de saida do MCP (V14.5, 2026-06-14)
==============================================================================
Objetivo: REDUZIR consumo de tokens do Claude. Toda tool do `lilo_mcp.py`
retorna texto que entra no contexto do cliente (Claude Desktop / Code). Sem um
teto, saidas grandes (busca academica ampla, `villa_pipeline`, `run_shell`,
`fs_search`, `grep_and_read`) podem injetar dezenas de milhares de tokens de
uma so vez.

Esta guarda e aplicada num unico ponto -- o decorator `_profile_tool` em
`lilo_mcp.py` -- entao cobre TODAS as tools, atuais e futuras, sem tocar em
cada funcao.

Principios (alinhados a filosofia do LILO: "nenhum default quebra comportamento"):
  - Saidas pequenas passam intactas (no-op). So saidas genuinamente grandes
    sao cortadas, entao o caso comum nao muda em nada.
  - Preserva INICIO + FIM (head+tail). Em logs e shell os erros costumam estar
    no fim; em listas/relatorios o cabecalho e o inicio. O miolo e o que menos
    importa quando algo e gigante.
  - Marcador claro e legivel pelo modelo no ponto do corte, com instrucao de
    como obter o resto (refinar query/limit) -- assim o Claude sabe que houve
    truncamento e nao alucina "fim de arquivo".
  - Configuravel por env, com kill-switch.

Env:
  LILO_MCP_MAX_CHARS   teto de caracteres por saida (default 48000 ~= 12k tokens).
                       0 ou negativo desliga a guarda (sem teto).
  LILO_MCP_HEAD_RATIO  fracao do orcamento dada ao inicio (default 0.7).
"""

from __future__ import annotations

import os

DEFAULT_MAX_CHARS = 48000
DEFAULT_HEAD_RATIO = 0.7
# Piso de seguranca: nunca operar com um teto tao pequeno que mutile saidas
# triviais. Abaixo disso, tratamos como "desligado mal configurado".
_MIN_SANE_BUDGET = 800


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def get_budget() -> int:
    """Teto de chars vigente. <=0 significa 'sem teto' (guarda desligada)."""
    return _env_int("LILO_MCP_MAX_CHARS", DEFAULT_MAX_CHARS)


def clamp_output(text, max_chars: int | None = None) -> object:
    """Corta `text` para caber em `max_chars`, preservando inicio e fim.

    - Nao-strings retornam intactas (FastMCP serializa o resto).
    - max_chars None -> le do env. <=0 -> sem corte.
    - Saida <= teto -> intacta (no-op; caso comum).

    O marcador inserido informa quantos chars foram omitidos e como obter mais,
    para o modelo nao tratar a saida cortada como completa.
    """
    if not isinstance(text, str):
        return text

    budget = get_budget() if max_chars is None else int(max_chars)
    if budget <= 0:
        return text  # guarda desligada
    if budget < _MIN_SANE_BUDGET:
        budget = _MIN_SANE_BUDGET

    total = len(text)
    if total <= budget:
        return text  # no-op -- caso comum

    omitted = total - budget
    marker = (
        "\n\n[...LILO truncou %s caracteres (%s -> %s) para economizar tokens. "
        "Para ver o trecho omitido, refine a busca, reduza `limit`/`max_results` "
        "ou peca a secao especifica. Ajuste o teto com LILO_MCP_MAX_CHARS...]\n\n"
        % (f"{omitted:,}", f"{total:,}", f"{budget:,}")
    )

    # Orcamento liquido para conteudo (descontando o marcador).
    content_budget = budget - len(marker)
    if content_budget < 200:
        # Teto minusculo: devolve so o inicio + nota curta.
        return text[: max(0, budget - 40)] + "\n[...truncado]"

    ratio = _env_float("LILO_MCP_HEAD_RATIO", DEFAULT_HEAD_RATIO)
    if ratio < 0.0 or ratio > 1.0:
        ratio = DEFAULT_HEAD_RATIO
    head_len = int(content_budget * ratio)
    tail_len = content_budget - head_len

    head = text[:head_len]
    tail = text[total - tail_len:] if tail_len > 0 else ""
    return head + marker + tail
