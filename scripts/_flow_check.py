#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Prova o fluxo do run() editado SEM importar o ScholarAgent (que o mount
# serve cacheado neste sandbox). Replica o trecho exato + o _format_results.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import research_sources as rs

_EXTERNAL = {"clinicaltrials", "opentargets", "npi", "crossref", "semanticscholar"}
_ALL = ["pubmed", "clinicaltrials", "opentargets", "npi", "crossref", "semanticscholar"]


def _format_results(results):  # idêntico ao do ScholarAgent
    lines = []
    for i, r in enumerate(results, 1):
        lines.append("%d. **%s**\n   Autores: %s (%s) — %s\n   %s" %
                     (i, r["title"], r["authors"], r["year"], r["source"], r["url"]))
    return "\n\n".join(lines)


def run_like(query, source, max_results=2):
    results = []
    if source == "all":
        results += rs.search_all(query, _ALL, max_results=max_results).get("results", [])
    elif source in _EXTERNAL:
        results += rs._DISPATCH[source](query, max_results)
    for r in results:
        r.setdefault("pmid", r.get("id", ""))
        r.setdefault("source", "")
        r.setdefault("authors", "")
        r.setdefault("year", "")
    if not results:
        return "(nenhum)"
    return _format_results(results)


for src, q in [("clinicaltrials", "dengue vaccine"), ("opentargets", "Parkinson"),
               ("crossref", "CRISPR gene editing"), ("npi", "cardiology")]:
    out = run_like(q, src)
    print("=== source=%s q=%s ===" % (src, q))
    print(out[:240])
    print()
print("=== source=all (malaria) ===")
print(run_like("malaria", "all", 1)[:500])
