"""
verify/ollama_judge.py — Constrói o LLM-judge local (Lilo 3.0 / Ollama, porta 11435).
Isola a única dependência de rede; a importação de httpx é lazy, então o pacote core
não exige httpx instalado para rodar (e os testes usam juízes fake).
"""
from __future__ import annotations
import json

from .prompts import nli_prompt
from ..config import LLM_URL as OLLAMA_URL, LLM_MODEL as DEFAULT_MODEL

_VALID = ("supported", "contradicted", "partial", "not_enough_info")


def make_ollama_judge(url: str = OLLAMA_URL, model: str = DEFAULT_MODEL, timeout: int = 120):
    """Retorna judge(claim, evidence) -> (verdict, confidence, rationale)."""
    import httpx  # lazy

    def judge(claim_text: str, evidence_text: str):
        try:
            r = httpx.post(url, json={
                "model": model,
                "prompt": nli_prompt(claim_text, evidence_text),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0},
            }, timeout=timeout)
            data = json.loads(r.json().get("response", "{}"))
            verdict = str(data.get("verdict", "not_enough_info")).lower().strip()
            if verdict not in _VALID:
                verdict = "not_enough_info"     # default conservador
            conf = float(data.get("confidence", 0.5))
            rationale = str(data.get("rationale", ""))[:200]
            return verdict, conf, rationale
        except Exception:
            # Falha de rede/parse → conservador: não sustenta.
            return "not_enough_info", 0.0, "Falha ao consultar o juiz local."

    return judge
