#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/bench_semantic_domains.py — Bench semântico multi-domínio do LILO.

V10.3 (2026-05-31). Pedido por Dione: testar o LILO em seus diferentes
agentes com FRASES SEMÂNTICAS que devem retornar resultados em áreas como
conhecimentos gerais, história, geografia, química, biologia, física,
matemática, agropecuária e veterinária — analisando a QUALIDADE do output,
os BUGS produzidos e o TEMPO de resposta em 1, 2 e 3 iterações.

V10.9 (2026-06-08): guarda de timeout PORTÁVEL (Windows-safe). Antes o
harness usava signal.SIGALRM, que NÃO existe no Windows — logo has_alarm
era False e NENHUMA guarda de travamento disparava: uma chamada lenta do
Ollama podia bloquear o bench indefinidamente e a métrica "froze" jamais
ficava True. Agora cada corrida roda em um thread próprio e
future.result(timeout) marca froze=True sem bloquear o restante (o thread
órfão segue em background até o processo encerrar). Assim o protocolo
"analisar... se travar" passa a ser medido de fato também no Windows.
ATENÇÃO: com Ollama real, estágios legítimos podem levar dezenas de
segundos — use --timeout generoso (ex.: 240) para não marcar travamento
falso.

O harness mede, por (domínio × iterações):
  - wall-clock (s) e se TRAVOU (timeout de guarda portável);
  - se houve BUG REAL (exceção Python) vs DEGRADAÇÃO esperada (stage sem
    LLM em modo mock retorna "[... ERRO apos N tentativas]");
  - o CAMINHO de roteamento (fast-path / delegação a especialista / pipeline);
  - o ESPECIALISTA/domínio escolhido (via explain_routing);
  - um SCORE de qualidade estrutural (0-100): heurístico no sandbox em modo
    mock; em ambiente real (Ollama quente) reflete densidade técnica do texto.

Saídas: JSON detalhado em docs/relatorios/.

Uso:
    python scripts/bench_semantic_domains.py                 # iters 1,2,3
    python scripts/bench_semantic_domains.py --iters 1,2     # subconjunto
    python scripts/bench_semantic_domains.py --timeout 240   # guarda por corrida
    LILO_SERVER_PROFILE=desktop_dev python scripts/bench_semantic_domains.py

Nota: para realmente exercitar 3 iterações, use um perfil cujo teto
max_iterations >= 3 (ex.: desktop_dev). Perfis enxutos (cowork/bio=2) capam.
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Frases semânticas por domínio (português, nível pesquisador).
DOMAIN_QUERIES = {
    "conhecimentos_gerais": "Quais são os pilares de uma dieta equilibrada e como afetam o metabolismo energético?",
    "historia": "Explique as principais causas econômicas e sociais da Revolução Francesa.",
    "geografia": "Descreva a formação e a importância das bacias hidrográficas do Brasil.",
    "quimica": "Detalhe o mecanismo da esterificação de Fischer, incluindo catálise ácida e equilíbrio.",
    "biologia": "Como funciona a replicação do DNA em eucariotos? Cite enzimas e etapas.",
    "fisica": "Explique o princípio da incerteza de Heisenberg e suas implicações físicas.",
    "matematica": "Enuncie e demonstre o teorema fundamental do cálculo.",
    "agropecuaria": "Quais fatores edafoclimáticos afetam a produtividade da soja no cerrado brasileiro?",
    "veterinaria": "Quais são os sinais clínicos, o diagnóstico e o manejo da cinomose em cães?",
}


def _quality_score(text: str) -> int:
    """Heurística 0-100 de qualidade estrutural do output."""
    if not text:
        return 0
    t = str(text)
    if "ERRO apos" in t:
        return 5
    score = 0
    if "[MOCK]" in t:
        score -= 20
    if len(t) >= 200:
        score += 25
    if len(t) >= 800:
        score += 15
    if any(h in t for h in ("##", "###", "Resumo", "Resultado", "Relatorio",
                            "Plano", "Discussao")):
        score += 20
    digits = sum(c.isdigit() for c in t)
    score += min(15, digits // 3)
    for kw in ("portanto", "mecanismo", "equacao", "enzima", "teorema",
               "hidrografica", "catalise", "clinic", "metabol", "incerteza"):
        if kw.lower() in t.lower():
            score += 3
    return max(0, min(100, score))


def _classify_path(text: str) -> str:
    if not text:
        return "vazio"
    if "Fast Path" in text or "skip-to-reporter" in text:
        return "fast-path"
    if "Delegacao a Especialista" in text:
        return "delegacao"
    if "Pipeline" in text:
        return "pipeline"
    if "Erro" in text[:40]:
        return "erro"
    return "outro"


def run_bench(iters_list, timeout_s):
    # V10.9: guarda de timeout PORTÁVEL via threads (Windows-safe). Ver
    # docstring do módulo. Substitui o antigo signal.SIGALRM (no-op no Windows).
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as _FutTimeout
    from functools import partial as _partial
    from agents.villa_lobos.agent import VillaLobosAgent
    try:
        from shared.server_profile import get_server_profile, get_profile_policy
        profile = get_server_profile()
        cap = get_profile_policy().get("max_iterations")
    except Exception:
        profile, cap = "?", None

    agent = VillaLobosAgent()
    # Detecta modo degradado (backend mock/ausente) para NAO contar
    # "[... ERRO apos N tentativas]" de stage sem LLM como bug de codigo.
    try:
        backend = getattr(agent.client, "backend", "unknown")
    except Exception:
        backend = "unknown"
    degraded_mode = (backend == "mock")

    rows = []
    for domain, query in DOMAIN_QUERIES.items():
        try:
            route = agent.explain_routing(query, allow_delegate=True)
            # explain_routing expoe 'delegate_target' (string|None), nao
            # 'delegate' (dict). A leitura antiga ('delegate').get('agent')
            # era sempre None -> a telemetria de route_domain jamais refletia
            # o alvo de delegacao; caia em domain_heuristic/'geral' por acaso.
            route_dom = route.get("delegate_target") \
                or route.get("domain_heuristic") or "geral"
            complexity = (route.get("decision") or {}).get("complexity", "?")
        except Exception as e:  # noqa: BLE001
            route_dom, complexity = "erro:%s" % e, "?"

        for it in iters_list:
            froze, bug, degraded, err = False, False, False, ""
            t0 = time.time()
            _ex = ThreadPoolExecutor(max_workers=1)
            _fut = _ex.submit(_partial(
                agent.run, query,
                context={"iterations": it, "allow_delegate": True}))
            try:
                out = _fut.result(timeout=timeout_s)
                out = out if isinstance(out, str) else str(out)
            except _FutTimeout:
                froze, out = True, "<TIMEOUT %ds>" % timeout_s
            except Exception as e:  # noqa: BLE001
                bug, err, out = True, str(e), "<EXC %s>" % e
            finally:
                # Nao esperar threads orfaos: uma corrida travada segue em
                # background ate o processo encerrar; libera o loop ja.
                _ex.shutdown(wait=False)
            dt = round(time.time() - t0, 3)
            if "<EXC" in out:
                bug = True
            elif "ERRO apos" in out:
                if degraded_mode:
                    degraded = True
                else:
                    bug = True
            rows.append({
                "domain": domain,
                "iters_requested": it,
                "route_domain": route_dom,
                "complexity": complexity,
                "wall_s": dt,
                "froze": froze,
                "bug": bug,
                "degraded": degraded,
                "error": err,
                "path": _classify_path(out),
                "quality": _quality_score(out),
                "out_len": len(out),
            })
    return rows, profile, cap, backend, degraded_mode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", default="1,2,3")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    iters_list = [int(x) for x in args.iters.split(",") if x.strip()]

    rows, profile, cap, backend, degraded_mode = run_bench(iters_list, args.timeout)

    n = len(rows)
    froze_n = sum(r["froze"] for r in rows)
    bug_n = sum(r["bug"] for r in rows)
    degraded_n = sum(r.get("degraded") for r in rows)
    avg_q = round(sum(r["quality"] for r in rows) / n, 1) if n else 0
    by_iter = {}
    for it in iters_list:
        sub = [r for r in rows if r["iters_requested"] == it]
        if sub:
            by_iter[it] = {
                "avg_wall_s": round(sum(r["wall_s"] for r in sub) / len(sub), 3),
                "avg_quality": round(sum(r["quality"] for r in sub) / len(sub), 1),
                "bugs": sum(r["bug"] for r in sub),
                "degraded": sum(r.get("degraded") for r in sub),
                "froze": sum(r["froze"] for r in sub),
            }

    report = {
        "date": date.today().isoformat(),
        "profile": profile,
        "backend": backend,
        "degraded_mode": degraded_mode,
        "max_iterations_cap": cap,
        "iters_tested": iters_list,
        "totals": {"runs": n, "froze": froze_n, "bugs": bug_n,
                   "degraded": degraded_n, "avg_quality": avg_q},
        "by_iter": by_iter,
        "rows": rows,
    }

    out_dir = _ROOT / "docs" / "relatorios"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = Path(args.out) if args.out else (
        out_dir / ("bench_semantic_%s.json" % date.today().isoformat()))
    # Escrita ATOMICA (tmp + os.replace): evita a classe de arquivo
    # meio-escrito/truncado que corrompeu agent.py e o test file quando uma
    # gravacao foi interrompida (limite de creditos). Ver relatorio 2026-06-04.
    import os
    _payload = json.dumps(report, ensure_ascii=False, indent=2)
    _tmp = out_json.with_suffix(out_json.suffix + ".tmp")
    _tmp.write_text(_payload, encoding="utf-8")
    os.replace(_tmp, out_json)

    print("== Bench semântico multi-domínio LILO ==")
    print("perfil=%s  backend=%s  degradado=%s  teto_iter=%s  iters=%s  corridas=%d" %
          (profile, backend, degraded_mode, cap, iters_list, n))
    print("travou=%d  bugs_reais=%d  degradado(sem_LLM)=%d  qualidade_media=%.1f" %
          (froze_n, bug_n, degraded_n, avg_q))
    print("\n%-22s %5s %7s %5s %4s %4s %4s %s" %
          ("dominio", "iters", "wall_s", "qual", "bug", "deg", "trv", "path"))
    for r in rows:
        print("%-22s %5d %7.2f %5d %4s %4s %4s %s" %
              (r["domain"], r["iters_requested"], r["wall_s"], r["quality"],
               "S" if r["bug"] else "-", "S" if r.get("degraded") else "-",
               "S" if r["froze"] else "-", r["path"]))
    print("\npor iteração:", json.dumps(by_iter, ensure_ascii=False))
    print("JSON salvo em:", out_json)
    return report


if __name__ == "__main__":
    main()
