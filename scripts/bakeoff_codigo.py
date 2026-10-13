"""Bake-off de codigo: o modelo escreve 3 funcoes Python e os testes escondidos rodam de verdade.

    python scripts\\bakeoff_codigo.py --modelos lilo,lilo-30b,lilo-32b,lilo-oss

Responde "e bom coder?" com fatos: acertos/3 (os testes passam no Python do env), tempo de
geracao e tok/s do Ollama (think desligado, sem opcoes de runner). Respeita o interruptor de GPU.
Modelos que nao cabem na GPU rodam hibridos: o tempo mostra o custo.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402

from lilo_host.comum import OLLAMA, gpu_reservada  # noqa: E402

TAREFAS = (
    ("Escreva só o código Python de uma função `fatorial(n)` que devolve n! para inteiros >= 0 e levanta "
     "ValueError para negativos. Sem explicações, só o código.",
     "assert fatorial(0) == 1\nassert fatorial(5) == 120\nassert fatorial(10) == 3628800\n"
     "try:\n    fatorial(-1)\n    raise SystemExit(1)\nexcept ValueError:\n    pass\n"),
    ("Escreva só o código Python de uma função `rle(s)` de codificação run-length: 'aaabcc' -> 'a3b1c2'; "
     "string vazia -> ''. Sem explicações, só o código.",
     "assert rle('aaabcc') == 'a3b1c2'\nassert rle('') == ''\nassert rle('a') == 'a1'\nassert rle('abbbba') == 'a1b4a1'\n"),
    ("Escreva só o código Python de uma função `mediana(xs)` que devolve a mediana de uma lista de números "
     "(média dos dois centrais se o tamanho for par) e levanta ValueError para lista vazia. Sem explicações.",
     "assert mediana([3, 1, 2]) == 2\nassert mediana([1, 2, 3, 4]) == 2.5\nassert mediana([5]) == 5\n"
     "try:\n    mediana([])\n    raise SystemExit(1)\nexcept ValueError:\n    pass\n"),
)


def _codigo(texto: str) -> str:
    blocos = re.findall(r"```(?:python)?\s*\n(.*?)```", texto, re.DOTALL)
    return (blocos[0] if blocos else texto).strip() + "\n"


def _gerar(modelo: str, pedido: str) -> tuple[str, float, float]:
    t0 = time.perf_counter()
    r = httpx.post(f"{OLLAMA}/api/chat", timeout=600, json={
        "model": modelo, "stream": False, "think": False,
        "messages": [{"role": "user", "content": pedido}]})
    r.raise_for_status()
    d = r.json()
    tps = d.get("eval_count", 0) / max(d.get("eval_duration", 1) / 1e9, 1e-6)
    return d["message"]["content"], time.perf_counter() - t0, tps


def _testar(codigo: str, testes: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        arq = Path(td) / "t.py"
        arq.write_text(codigo + "\n" + testes, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, str(arq)], capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return False, "timeout"
        return p.returncode == 0, (p.stderr or p.stdout).strip().splitlines()[-1:] and (p.stderr or p.stdout).strip().splitlines()[-1] or ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modelos", default="lilo")
    a = ap.parse_args()
    motivo = gpu_reservada()
    if motivo:
        print("GPU reservada (%s): nao carrego modelo." % motivo)
        return 1
    for modelo in a.modelos.split(","):
        print("\n=== %s" % modelo)
        acertos, tempos, tpss = 0, [], []
        for pedido, testes in TAREFAS:
            try:
                texto, seg, tps = _gerar(modelo, pedido)
            except httpx.HTTPError as e:
                print("  ERR  %s" % e)
                tempos.append(0.0)
                continue
            ok, detalhe = _testar(_codigo(texto), testes)
            acertos += ok
            tempos.append(seg)
            tpss.append(tps)
            print("  %s %6.1fs %5.1f tok/s  %s" % ("OK " if ok else "ERR", seg, tps, "" if ok else detalhe[:70]))
        print("  acertos %d/%d | tempo medio %.1fs | %.1f tok/s" % (
            acertos, len(TAREFAS), sum(tempos) / len(tempos), sum(tpss) / max(1, len(tpss))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
