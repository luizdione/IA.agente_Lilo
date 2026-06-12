#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
journal_calibration.py — camada de LEITURA/CONSUMO dos perfis de revista
aprendidos por build_journal_profile.py (ML a partir de OpenAlex/Europe PMC).

É a ponte entre a skill build_paper e os módulos de "Produção de Texto" das
plataformas (Streamlit do genomas, Shiny do epigenoma). Sem dependências
pesadas: só stdlib para LER/CALIBRAR. O aprendizado (rede) fica em
build_journal_profile.py; aqui apenas consumimos o artefato JSON.

API:
  load_profile(journal, extra_dirs=None) -> dict | None
  section_targets(journal, ...)          -> {secao: {target, source, basis}}
  calibration_summary(journal, ...)      -> dict pronto p/ UI (PT)
  as_json(journal, ...)                  -> str JSON (p/ bridges R/CLI)

Metas de seção: usa a NORMA EMPÍRICA do periódico quando existir (mediana de
artigos reais); senão, cai no piso do CLAUDE.md. O abstract é calibrado pela
mediana real (ex.: Animal Genetics ~232 palavras, não os 350 genéricos).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

# Piso genérico do CLAUDE.md (fallback quando não há norma empírica da revista).
CLAUDE_MIN = {
    "abstract": 350, "introduction": 600, "methods": 700,
    "results": 900, "discussion": 700, "conclusion": 200,
}

# Diretórios de perfis padrão. O MESMO arquivo serve à skill e às cópias
# vendoradas nas plataformas: procuramos o layout da skill
# (../journals/profiles) e o layout vendorado (./profiles).
_HERE = Path(__file__).resolve().parent
_DEFAULT_PROFILE_DIRS = [
    _HERE.parent / "journals" / "profiles",   # layout da skill
    _HERE / "profiles",                        # layout vendorado na plataforma
]


def slug(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s or "")
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _candidate_dirs(extra_dirs=None):
    dirs = []
    for d in (extra_dirs or []):
        if d:
            dirs.append(Path(d))
    dirs.extend(_DEFAULT_PROFILE_DIRS)
    seen, out = set(), []
    for d in dirs:
        k = str(d)
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


def load_profile(journal: str, extra_dirs=None) -> dict | None:
    """Carrega o perfil JSON de uma revista (por nome ou slug). Procura em
    extra_dirs (cache local da plataforma) e depois no diretório da skill."""
    target = slug(journal)
    for d in _candidate_dirs(extra_dirs):
        if not d or not d.exists():
            continue
        cand = d / f"{target}.json"
        if cand.exists():
            try:
                return json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                continue
        # tolera nome ligeiramente diferente
        for f in d.glob("*.json"):
            try:
                p = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if slug(p.get("journal", "")) == target:
                return p
    return None


def _median_words(stats_block) -> int | None:
    try:
        w = stats_block.get("words") or {}
        m = w.get("median")
        return int(round(m)) if m is not None else None
    except Exception:
        return None


def section_targets(journal: str, *, extra_dirs=None,
                    fallback: dict | None = None) -> dict:
    """Metas calibradas por seção. Cada item:
       {target:int, source:'ml'|'claude', basis:str}.
    Usa norma empírica (mediana) quando disponível; senão piso CLAUDE.md."""
    fb = dict(CLAUDE_MIN)
    if fallback:
        fb.update(fallback)
    prof = load_profile(journal, extra_dirs)
    out = {}
    norms = (prof or {}).get("section_norms", {}) or {}
    abs_stats = (prof or {}).get("abstract_stats", {}) or {}

    for sec, default in fb.items():
        ml_val = None
        if sec == "abstract":
            ml_val = _median_words(abs_stats)
        elif sec in norms:
            ml_val = _median_words(norms[sec])
        if ml_val:
            n = ((abs_stats.get("words") or {}).get("n")
                 if sec == "abstract"
                 else (norms.get(sec, {}).get("words") or {}).get("n"))
            out[sec] = {"target": ml_val, "source": "ml",
                        "basis": f"mediana de {n} artigos reais"}
        else:
            out[sec] = {"target": default, "source": "claude",
                        "basis": "piso CLAUDE.md (sem norma empírica)"}
    return out


def calibration_summary(journal: str, *, extra_dirs=None) -> dict:
    """Resumo pronto para exibir na UI (PT)."""
    prof = load_profile(journal, extra_dirs)
    if not prof:
        return {"journal": journal, "available": False,
                "message": ("Sem perfil aprendido. Rode "
                            "build_journal_profile.py para calibrar.")}
    abs_w = (prof.get("abstract_stats", {}).get("words") or {})
    refs = (prof.get("references_stats", {}).get("count_per_article") or {})
    sem = prof.get("semantics", {}) or {}
    prov = prof.get("provenance", {}) or {}
    return {
        "journal": prof.get("journal", journal),
        "available": True,
        "issn": prof.get("issn", []),
        "abstract_median_words": abs_w.get("median"),
        "abstract_p25": abs_w.get("p25"),
        "abstract_p75": abs_w.get("p75"),
        "abstract_max": abs_w.get("max"),
        "refs_median": refs.get("median"),
        "refs_range": ([refs.get("min"), refs.get("max")]
                       if refs.get("min") is not None else None),
        "avg_sentence_words": sem.get("avg_sentence_words"),
        "top_connectives": list((sem.get("connectives") or {}).keys())[:5],
        "citation_in_text": (prof.get("citation", {}) or {}).get("in_text"),
        "n_sampled": prov.get("n_sampled"),
        "n_fulltext": prov.get("n_fulltext"),
        "built": prov.get("built"),
        "note": prov.get("note"),
        "targets": section_targets(journal, extra_dirs=extra_dirs),
    }


def as_json(journal: str, *, extra_dirs=None) -> str:
    return json.dumps(calibration_summary(journal, extra_dirs=extra_dirs),
                      ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    j = sys.argv[1] if len(sys.argv) > 1 else "Animal Genetics"
    print(as_json(j))
