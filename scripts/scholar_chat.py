"""
scripts/chat.py — REPL de conversa com a biblioteca, com gate de verificação opcional.
Uso: python scripts/chat.py [--verify]
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scholaragent.brain.embedder import Embedder
from scholaragent.brain.vector_store import BrainStore
from scholaragent.chat.rag_chain import ScholarRAG


def main(verify: bool = False):
    embedder = Embedder()
    store = BrainStore()
    rag = ScholarRAG(store, embedder)

    gate = bridge = None
    if verify:
        from scholaragent.verify import build_grounder, VerificationGate, evidence_from_rag
        gate = VerificationGate(build_grounder(store, embedder))
        bridge = evidence_from_rag

    print("ScholarAgent — pergunte à biblioteca (Ctrl+C para sair).")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        res = rag.ask(q)
        print("\n" + res["answer"])
        for r in res["refs"]:
            print("  " + r)
        if gate and res["chunks"]:
            used, ref_map = bridge(res["chunks"], res["metas"])
            report = gate.verify("chat", q, res["answer"], used, ref_map, write_trail=False)
            print(f"\n[gate] decisão: {report.decision.value.upper()}")


if __name__ == "__main__":
    main(verify="--verify" in sys.argv)
