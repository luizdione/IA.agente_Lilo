"""Portao G4 da biblioteca: teste de item conhecido + latencia de busca.

    python scripts\\avaliar_biblioteca.py              # 30 PDFs sorteados (semente 14)
    python scripts\\avaliar_biblioteca.py --n 50 --semente 7

Para cada PDF sorteado pega um trecho do meio e pede ao `lilo` (Ollama, think desligado)
uma pergunta curta que esse trecho responde; sem Ollama, usa a 1a frase do trecho. Depois
busca a pergunta e confere se o PDF de origem esta no top-5. Passa com >= 80% de acertos
e p95 da busca < 1,5 s (busca na CPU, modelo ja carregado). Codigo de saida 1 se falhar.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from lilo_host import biblioteca as B  # noqa: E402
from lilo_host.comum import MODELO, OLLAMA, gpu_reservada  # noqa: E402

PEDIDO = ("Escreva UMA pergunta curta (ate 20 palavras), em ingles, que o trecho abaixo responde. "
          "Responda so com a pergunta.\n\n%s")


def _pergunta(trecho: str) -> tuple[str, str]:
    """(pergunta, origem): pelo lilo ou, sem GPU/Ollama, a 1a frase do trecho."""
    if not gpu_reservada():
        try:
            r = httpx.post(f"{OLLAMA}/api/chat", timeout=120,
                           json={"model": MODELO, "stream": False, "think": False,
                                 "messages": [{"role": "user", "content": PEDIDO % trecho[:1500]}]})
            q = " ".join(r.json()["message"]["content"].split()).strip('"')
            if 5 <= len(q) <= 300:
                return q, "lilo"
        except (httpx.HTTPError, KeyError, ValueError):
            pass
    frase = re.split(r"(?<=[.!?])\s+", trecho.strip())[0]
    return frase[:200], "frase"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--semente", type=int, default=14)
    ap.add_argument("--indice", default="")
    a = ap.parse_args()
    indice = Path(a.indice) if a.indice else B.INDICE
    con = B._db(indice)
    docs = con.execute("SELECT hash, nome FROM docs WHERE erro IS NULL AND trechos >= 3").fetchall()
    if len(docs) < a.n:
        print("so %d documentos com texto no indice; preciso de %d" % (len(docs), a.n))
        return 1
    random.seed(a.semente)
    sorteados = random.sample(docs, a.n)
    print("indice: %s | docs com texto: %d | amostra: %d" % (indice, len(docs), a.n))

    B.embedder_consulta()                      # carrega antes de cronometrar
    acertos, tempos, origens = 0, [], {"lilo": 0, "frase": 0}
    for h, nome in sorteados:
        trechos = con.execute("SELECT texto FROM trechos WHERE hash=? ORDER BY idx", (h,)).fetchall()
        trecho = trechos[len(trechos) // 2][0]
        q, origem = _pergunta(trecho)
        origens[origem] += 1
        t0 = time.perf_counter()
        r = B.buscar(q, n=5, indice=indice)
        tempos.append(time.perf_counter() - t0)
        achou = isinstance(r, list) and any(x["arquivo"] == nome for x in r)
        acertos += achou
        print("%s %5.2fs  %-60s  <- %s" % ("OK " if achou else "ERR", tempos[-1], q[:60], nome[:45]))
    con.close()
    taxa = acertos / a.n
    p95 = sorted(tempos)[max(0, int(round(0.95 * len(tempos))) - 1)]
    print("\nitem conhecido no top-5: %d/%d = %.0f%%  (perguntas: %d pelo lilo, %d por frase)" % (
        acertos, a.n, 100 * taxa, origens["lilo"], origens["frase"]))
    print("busca: p50 %.2fs  p95 %.2fs  max %.2fs" % (sorted(tempos)[len(tempos) // 2], p95, max(tempos)))
    falhas = []
    if taxa < 0.8:
        falhas.append("acertos %.0f%% < 80%%" % (100 * taxa))
    if p95 >= 1.5:
        falhas.append("p95 %.2fs >= 1.5s" % p95)
    print("PORTAO G4: " + ("PASSOU" if not falhas else "FALHOU - " + "; ".join(falhas)))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
