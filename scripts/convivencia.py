"""Portoes G1 (convivencia) e de recarga do LILO v14.

    python scripts\\convivencia.py             # G1: embeddings com o `lilo` residente
    python scripts\\convivencia.py --recarga   # descarrega o `lilo` e mede a 1a pergunta

G1: com o `lilo` na GPU, faz 50 embeddings no jina e 10 no bge-m3 (os dois
embedders que os outros plugins usam) e confere que o `lilo` continua 100% na
GPU e que o "2+2" segue com 1o token < 1 s. Se falhar, o plano manda fixar os
embedders na CPU (`PARAMETER num_gpu 0`).

Recarga: `keep_alive: 0` tira o `lilo` da GPU; a pergunta seguinte tem de
responder em <= 12 s (arquivos no cache de disco). Deixa o modelo carregado.

Respeita o interruptor de GPU do dono (saida 3 com ele em off). Codigo de
saida 1 se um portao falhar. Registra em %LOCALAPPDATA%\\LILO\\bench\\convivencia.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

SWITCH = Path(os.environ.get("OLLAMA_DELEGATE_DIR",
                             str(Path.home() / ".ollama_delegate"))) / "switch.json"
SAIDA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LILO" / "bench"

EMBEDDERS = (
    # (modelo, n chamadas, texto base) — jina e o embedder de codigo do lumen;
    # bge-m3 e o da biblioteca e da memoria.
    ("ordis/jina-embeddings-v2-base-code:latest", 50,
     "def soma(a, b):\n    return a + b  # caso {i}"),
    ("bge-m3:latest", 10,
     "A proteína NS1 do flavivírus interage com a membrana celular, amostra {i}."),
)


def _interruptor_off() -> bool:
    try:
        return json.loads(SWITCH.read_text(encoding="utf-8")).get("estado") != "on"
    except FileNotFoundError:
        return False
    except Exception:
        return True  # ilegivel = off: na duvida nao se carrega modelo


def _ps(cli: httpx.Client, base: str) -> dict[str, dict]:
    """Modelos carregados: nome -> {gpu_pct, size, size_vram}."""
    r = cli.get(f"{base}/api/ps")
    r.raise_for_status()
    out = {}
    for m in r.json().get("models", []):
        size, vram = m.get("size", 0), m.get("size_vram", 0)
        out[m["name"]] = {"gpu_pct": round(100 * vram / size) if size else 0,
                          "size": size, "size_vram": vram}
    return out


def _chat(cli: httpx.Client, base: str, modelo: str, pergunta: str) -> dict:
    """Uma pergunta em streaming: tempo ate o 1o token e tempo de carga."""
    corpo = {"model": modelo, "stream": True, "think": False,
             "messages": [{"role": "user", "content": pergunta}]}
    t0 = time.perf_counter()
    ttft = None
    fim: dict = {}
    with cli.stream("POST", f"{base}/api/chat", json=corpo) as r:
        r.raise_for_status()
        for linha in r.iter_lines():
            if not linha:
                continue
            ev = json.loads(linha)
            if ttft is None and ev.get("message", {}).get("content"):
                ttft = time.perf_counter() - t0
            if ev.get("done"):
                fim = ev
    return {"ttft": round(ttft if ttft is not None else time.perf_counter() - t0, 3),
            "total": round(time.perf_counter() - t0, 3),
            "carga": round(fim.get("load_duration", 0) / 1e9, 2)}


def _embed(cli: httpx.Client, base: str, modelo: str, texto: str) -> float:
    t0 = time.perf_counter()
    r = cli.post(f"{base}/api/embed", json={"model": modelo, "input": texto})
    r.raise_for_status()
    return time.perf_counter() - t0


def _registrar(linha: dict) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    linha["quando"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with (SAIDA / "convivencia.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def _garantir_residente(cli: httpx.Client, base: str, modelo: str) -> None:
    if f"{modelo}:latest" not in _ps(cli, base):
        print(f"{modelo} nao estava carregado; aquecendo...")
        r = _chat(cli, base, modelo, "Responda apenas: pronto")
        print(f"  carregado em {r['total']} s (carga {r['carga']} s)")


def portao_g1(cli: httpx.Client, base: str, modelo: str, limite: float) -> int:
    _garantir_residente(cli, base, modelo)
    antes = _ps(cli, base).get(f"{modelo}:latest", {})
    print(f"{modelo}: {antes.get('gpu_pct')}% GPU antes dos embeddings")

    tempos: dict[str, list[float]] = {}
    for emb, n, texto in EMBEDDERS:
        ts = [_embed(cli, base, emb, texto.format(i=i)) for i in range(n)]
        tempos[emb] = ts
        print(f"  {emb}: {n} embeddings, 1o {ts[0]:.2f} s (carga), "
              f"mediana {sorted(ts)[n // 2]:.3f} s, total {sum(ts):.1f} s")

    ps = _ps(cli, base)
    depois = ps.get(f"{modelo}:latest")
    for nome, m in ps.items():
        print(f"  carregado: {nome}  {m['gpu_pct']}% GPU  "
              f"({m['size_vram'] / 2**30:.1f} GiB na VRAM)")

    amostras = [_chat(cli, base, modelo, "Quanto é 2+2?") for _ in range(3)]
    ttfts = [a["ttft"] for a in amostras]
    recargas = sum(1 for a in amostras if a["carga"] > 1.0)
    print(f"  '2+2' depois: ttft {ttfts} s, recargas {recargas}")

    falhas = []
    if depois is None:
        falhas.append(f"{modelo} foi despejado da GPU pelos embeddings")
    elif depois["gpu_pct"] < 100:
        falhas.append(f"{modelo} ficou {depois['gpu_pct']}% GPU (derramou para a CPU)")
    if max(ttfts) >= limite:
        falhas.append(f"TTFT max {max(ttfts)} s >= {limite} s")
    if recargas:
        falhas.append(f"{recargas} recarga(s) do {modelo}")

    _registrar({"portao": "G1", "modelo": modelo, "gpu_pct_depois": depois and depois["gpu_pct"],
                "embedders": {e: {"n": len(t), "mediana": round(sorted(t)[len(t) // 2], 3)}
                              for e, t in tempos.items()},
                "ttft": ttfts, "recargas": recargas, "passou": not falhas})
    print("PORTAO G1: " + ("PASSOU" if not falhas else "FALHOU - " + "; ".join(falhas)))
    return 0 if not falhas else 1


def portao_recarga(cli: httpx.Client, base: str, modelo: str, limite: float) -> int:
    cli.post(f"{base}/api/generate", json={"model": modelo, "keep_alive": 0}).raise_for_status()
    for _ in range(20):
        if f"{modelo}:latest" not in _ps(cli, base):
            break
        time.sleep(0.5)
    else:
        print(f"{modelo} nao descarregou; portao nao medido")
        return 1
    print(f"{modelo} descarregado; perguntando...")
    r = _chat(cli, base, modelo, "Quanto é 2+2?")
    print(f"  1o token em {r['ttft']} s (carga {r['carga']} s, total {r['total']} s)")
    passou = r["ttft"] <= limite
    _registrar({"portao": "recarga", "modelo": modelo, **r, "passou": passou})
    print("PORTAO RECARGA: " + ("PASSOU" if passou else f"FALHOU - {r['ttft']} s > {limite} s"))
    return 0 if passou else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--recarga", action="store_true", help="portao de recarga em vez do G1")
    ap.add_argument("--modelo", default="lilo")
    ap.add_argument("--url", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ap.add_argument("--limite-ttft", type=float, default=1.0)
    ap.add_argument("--limite-recarga", type=float, default=12.0)
    a = ap.parse_args()

    if _interruptor_off():
        print(f"Interruptor de GPU em off ({SWITCH}): nada carregado. Quem religa e o dono.")
        return 3
    with httpx.Client(timeout=300) as cli:
        if a.recarga:
            return portao_recarga(cli, a.url, a.modelo, a.limite_recarga)
        return portao_g1(cli, a.url, a.modelo, a.limite_ttft)


if __name__ == "__main__":
    sys.exit(main())
