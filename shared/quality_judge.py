# -*- coding: utf-8 -*-
"""shared/quality_judge.py — Juiz LLM de qualidade com rubrica por domínio.

Motivação (relatorio_ia_lilo_2026-06-11_v2.md, seção "Próximas ações"):
o `_quality_score` do bench é heurístico (premia tamanho, cabeçalhos, dígitos
e keywords) e NÃO mede adequação ao domínio nem correção factual — justamente
o que o de-viés de prompt (V11.2) melhora. Resultado: o ganho qualitativo do
de-viés fica invisível no escore estrutural.

Este módulo introduz um JUIZ LLM que avalia a resposta contra uma RUBRICA por
domínio, devolvendo um escore 0-100 decomposto em 4 critérios de 0-25:
  - factual_accuracy : correção do conteúdo (sem erros nem invenções);
  - technical_depth   : profundidade e vocabulário próprios do domínio;
  - completeness      : cobertura de todas as partes pedidas na query;
  - clarity_structure : organização, precisão e ausência de enchimento.

Para reduzir AUTO-VIÉS, o modelo juiz é, por padrão, distinto e maior que o
avaliado (worker usa llama3.1:8b; juiz default phi3:14b). Configurável por
`LILO_JUDGE_MODEL` (ex.: um modelo cloud mais forte, se o perfil permitir).

Uso:
    from shared.quality_judge import judge_answer
    verdict = judge_answer(query, answer, domain="quimica")
    verdict["total"]          # 0-100 (ou None se o juiz falhar)
    verdict["criteria"]       # {factual_accuracy, technical_depth, ...}
"""

import json
import os
import re
from typing import Optional

from .llm_client import get_client, MODELS
from .logger import get_logger

log = get_logger("QualityJudge")

# Modelo juiz: distinto/maior que o avaliado p/ mitigar auto-viés. Override por
# env (inclusive p/ um modelo cloud mais forte, se o setup do servidor permitir).
JUDGE_MODEL = os.getenv(
    "LILO_JUDGE_MODEL",
    MODELS.get("plan", "phi3:14b-medium-128k-instruct-q4_K_M"),
)

# Foco da rubrica por domínio: o que um especialista da área valoriza. Mantém
# o juiz CALIBRADO ao domínio em vez de aplicar um molde único (que reintroduz
# viés). Domínio ausente -> foco genérico de rigor científico.
_DOMAIN_RUBRIC = {
    "conhecimentos_gerais": "precisão factual, equilíbrio e ausência de mitos populares",
    "historia": "causalidade, cronologia correta, atores e contexto socioeconômico",
    "geografia": "processos físicos, escalas, dados quantitativos e topônimos corretos",
    "quimica": "mecanismo de reação, estequiometria, nomenclatura e equilíbrio",
    "biologia": "enzimas, vias, estruturas moleculares e etapas dos processos",
    "fisica": "formalismo matemático, princípios, unidades coerentes e interpretação física",
    "matematica": "rigor, definições precisas, demonstração válida e notação correta",
    "agropecuaria": "fatores edafoclimáticos, manejo, dados agronômicos e nomes de cultivares/práticas",
    "veterinaria": "sinais clínicos, etiologia, diagnóstico diferencial e conduta terapêutica",
}

_JUDGE_SYSTEM = (
    "Voce e um avaliador cientifico rigoroso e imparcial. Avalia a QUALIDADE "
    "de uma resposta tecnica contra a pergunta, no nivel esperado de um "
    "pesquisador senior. Seja exigente: penalize erros factuais, invencoes, "
    "respostas rasas, partes nao respondidas e enchimento. NAO premie tamanho "
    "por si so. Responda APENAS JSON valido, sem markdown."
)


def _extract_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _clamp25(v) -> int:
    try:
        return max(0, min(25, int(round(float(v)))))
    except Exception:
        return 0


def judge_answer(query: str, answer: str, domain: str = "",
                 client=None, model: str = None) -> dict:
    """Avalia `answer` para `query` no `domain`. Devolve dict com:
       {total:0-100|None, criteria:{...}, justification:str, model, ok:bool}.
    Nunca lanca: em falha do juiz, total=None e ok=False (o caller decide).
    """
    foco = _DOMAIN_RUBRIC.get(domain, "rigor cientifico e correcao factual")
    # Trunca respostas muito longas p/ caber no contexto do juiz sem custo extra.
    ans = (answer or "").strip()
    if len(ans) > 6000:
        ans = ans[:6000] + "\n[...truncado para avaliacao...]"

    prompt = (
        "Avalie a RESPOSTA contra a PERGUNTA do dominio '%s'.\n"
        "Foco do dominio: %s.\n\n"
        "Atribua 0-25 a CADA criterio:\n"
        "- factual_accuracy: correcao do conteudo (sem erros nem invencoes);\n"
        "- technical_depth: profundidade e vocabulario proprios do dominio;\n"
        "- completeness: cobre TODAS as partes pedidas na pergunta;\n"
        "- clarity_structure: organizacao, precisao, sem enchimento.\n\n"
        "PERGUNTA:\n%s\n\nRESPOSTA:\n%s\n\n"
        "Responda APENAS JSON:\n"
        '{"factual_accuracy":int,"technical_depth":int,"completeness":int,'
        '"clarity_structure":int,"justification":"frase curta"}'
        % (domain or "geral", foco, query, ans)
    )
    cli = client or get_client()
    use_model = model or JUDGE_MODEL
    try:
        raw = cli.chat(prompt=prompt, system=_JUDGE_SYSTEM, model=use_model,
                       temperature=0.0, max_tokens=400)
    except Exception as e:
        log.warning("Juiz falhou (%s): %s", use_model, e)
        return {"total": None, "criteria": {}, "justification": "",
                "model": use_model, "ok": False, "error": str(e)}

    if not raw or raw.startswith("[MOCK]"):
        return {"total": None, "criteria": {}, "justification": "",
                "model": use_model, "ok": False, "error": "mock/empty"}

    data = _extract_json(raw)
    if not data:
        log.warning("Juiz devolveu JSON ilegivel: %s", str(raw)[:160])
        return {"total": None, "criteria": {}, "justification": "",
                "model": use_model, "ok": False, "error": "json_parse"}

    crit = {
        "factual_accuracy": _clamp25(data.get("factual_accuracy")),
        "technical_depth": _clamp25(data.get("technical_depth")),
        "completeness": _clamp25(data.get("completeness")),
        "clarity_structure": _clamp25(data.get("clarity_structure")),
    }
    total = sum(crit.values())
    return {
        "total": total,
        "criteria": crit,
        "justification": str(data.get("justification", ""))[:300],
        "model": use_model,
        "ok": True,
    }
