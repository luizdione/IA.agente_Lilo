#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Verificador transitorio da integracao de fontes no ScholarAgent (pode apagar).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.scholaragent.agent import ScholarAgent

ag = ScholarAgent()
for src, q in [("clinicaltrials", "dengue vaccine"),
               ("opentargets", "Parkinson"),
               ("crossref", "CRISPR gene editing"),
               ("npi", "cardiology")]:
    out = ag.run(q, context={"source": src, "synthesize": False, "max_results": 2})
    head = out.splitlines()[0] if out else "(vazio)"
    print("source=%-15s q=%-22s -> %s" % (src, q, head[:70]))

# Agregada
out = ag.run("malaria", context={"source": "all", "synthesize": False, "max_results": 1})
print("\n--- source=all (malaria) ---")
print(out[:600])
# enum exposto
tools = {t["name"]: t for t in ag.get_tools()}
print("\nenum source:", tools["scholar_search"]["inputSchema"]["properties"]["source"]["enum"])
