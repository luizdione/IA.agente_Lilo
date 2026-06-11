#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/_bench_compare.py - Compara as duas corridas mais recentes do
bench semantico multi-dominio (docs/relatorios/bench_semantic_*.json).

Adicionado no ciclo V11.0 (2026-06-09) para automatizar a etapa de ANALISE/
COMPARACAO do protocolo ia_lilo (antes feita a olho sobre o JSON). Reusavel
nos proximos ciclos.

Uso:
    python scripts/_bench_compare.py                 # 2 mais recentes
    python scripts/_bench_compare.py A.json B.json   # explicito (B=anterior)
"""
import json
import sys
from pathlib import Path

REL = Path(__file__).resolve().parents[1] / "docs" / "relatorios"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _pick():
    js = sorted(REL.glob("bench_semantic_*.json"))
    if len(js) < 2:
        return (js[-1], None) if js else (None, None)
    return js[-1], js[-2]


def _rows_by_domain(rep):
    d = {}
    for r in rep.get("rows", []):
        d.setdefault(r["domain"], {})[r["iters_requested"]] = r
    return d


def main():
    if len(sys.argv) >= 3:
        cur_p, prev_p = sys.argv[1], sys.argv[2]
    else:
        cur_p, prev_p = _pick()
    if not cur_p:
        print("Sem JSONs de bench.")
        return
    cur = _load(cur_p)
    print("== COMPARACAO BENCH SEMANTICO ==")
    print("atual   :", Path(cur_p).name, "| backend=%s perfil=%s degr=%s" % (
        cur.get("backend"), cur.get("profile"), cur.get("degraded_mode")))
    if prev_p:
        prev = _load(prev_p)
        print("anterior:", Path(prev_p).name, "| backend=%s degr=%s" % (
            prev.get("backend"), prev.get("degraded_mode")))
    else:
        prev = None
        print("anterior: (nenhum)")

    ct, pt = cur.get("totals", {}), (prev.get("totals", {}) if prev else {})
    print("\n-- TOTAIS --")
    print("              atual   anterior")
    for k in ("runs", "avg_quality", "bugs", "degraded", "froze"):
        print("%-12s  %-7s %-7s" % (k, ct.get(k), pt.get(k, "-")))

    print("\n-- POR ITERACAO (tempo medio s / qualidade media) --")
    cbi, pbi = cur.get("by_iter", {}), (prev.get("by_iter", {}) if prev else {})
    print("iter   wall_atual  q_atual   wall_ant   q_ant")
    for it in ("1", "2", "3"):
        c = cbi.get(it, {}) or cbi.get(int(it), {})
        p = pbi.get(it, {}) or pbi.get(int(it), {})
        print("%-5s  %-10s  %-7s   %-9s  %-6s" % (
            it, c.get("avg_wall_s"), c.get("avg_quality"),
            p.get("avg_wall_s", "-"), p.get("avg_quality", "-")))

    print("\n-- POR DOMINIO (qualidade @iter1/2/3 | path@1 | delta_qual_media) --")
    cd = _rows_by_domain(cur)
    pd = _rows_by_domain(prev) if prev else {}
    flags = []
    for dom in cd:
        q = [cd[dom].get(i, {}).get("quality") for i in (1, 2, 3)]
        path1 = cd[dom].get(1, {}).get("path")
        cavg = sum(x for x in q if isinstance(x, int)) / max(
            1, len([x for x in q if isinstance(x, int)]))
        delta = ""
        if dom in pd:
            pq = [pd[dom].get(i, {}).get("quality") for i in (1, 2, 3)]
            pavg = sum(x for x in pq if isinstance(x, int)) / max(
                1, len([x for x in pq if isinstance(x, int)]))
            delta = "%+.1f" % (cavg - pavg)
        print("%-22s %-12s %-10s %s" % (dom, "/".join(str(x) for x in q),
                                         path1, delta))
        for i in (1, 2, 3):
            r = cd[dom].get(i, {})
            if r.get("bug"):
                flags.append("BUG %s@%d: %s" % (dom, i, r.get("error", "")[:80]))
            if r.get("froze"):
                flags.append("FROZE %s@%d (wall=%ss)" % (dom, i, r.get("wall_s")))
            if isinstance(r.get("quality"), int) and r["quality"] < 55:
                flags.append("LOWQ %s@%d q=%d len=%s path=%s" % (
                    dom, i, r["quality"], r.get("out_len"), r.get("path")))

    print("\n-- FLAGS (bugs / travas / baixa qualidade <55) --")
    print("\n".join(flags) if flags else "nenhuma")


if __name__ == "__main__":
    main()
