"""Indexa a biblioteca de PDFs do dono (F3): incremental, resumivel, com arquivo de status.

    python scripts\\indexar_biblioteca.py                   # auto: GPU se livre (descarrega o lilo antes), senao CPU
    python scripts\\indexar_biblioteca.py --dispositivo cpu
    python scripts\\indexar_biblioteca.py --limite 20       # ensaio com os 20 primeiros PDFs
    python scripts\\indexar_biblioteca.py --status           # progresso e contagens
    python scripts\\indexar_biblioteca.py --falhas           # PDFs que falharam e por que

Roda em primeiro plano; `lilo.ps1 indexar` o poe em segundo plano com log em
<indice>\\indexar.log. Na GPU o `lilo` e descarregado antes (bge-m3 fp16 + lilo nao cabem
juntos com folga na 3060) e aquecido de novo ao fim, se o interruptor seguir on. Respeita o
orcamento de RAM (nao comeca acima de 80%).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from lilo_host import biblioteca  # noqa: E402
from lilo_host.comum import MODELO, OLLAMA, gpu_reservada  # noqa: E402


def _ram_pct() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().percent)
    except Exception:  # noqa: BLE001
        return 0


def _dispositivo_auto() -> str:
    if gpu_reservada():
        return "cpu"
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


def _lilo_descarregar() -> bool:
    try:
        r = httpx.post(f"{OLLAMA}/api/generate", json={"model": MODELO, "keep_alive": 0}, timeout=60)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _lilo_aquecer() -> None:
    if gpu_reservada():
        return
    try:
        httpx.post(f"{OLLAMA}/api/chat", json={"model": MODELO, "stream": False, "think": False,
                                               "messages": [{"role": "user", "content": "Responda apenas: pronto"}]},
                   timeout=300)
    except httpx.HTTPError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pasta", default="", help="pasta dos PDFs (padrao: LILO_BIBLIOTECA_PDFS)")
    ap.add_argument("--indice", default="", help="pasta do indice (padrao: LILO_BIBLIOTECA)")
    ap.add_argument("--dispositivo", choices=("auto", "cuda", "cpu"), default="auto")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--manter-lilo", action="store_true", help="nao descarregar o lilo na GPU")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--falhas", action="store_true")
    a = ap.parse_args()
    indice = Path(a.indice) if a.indice else None
    pasta = Path(a.pasta) if a.pasta else None

    if a.status:
        print(json.dumps(biblioteca.status(indice), ensure_ascii=False, indent=1))
        return 0
    if a.falhas:
        for f in biblioteca.falhas(indice):
            print("%s\t%s" % (f["arquivo"], f["erro"]))
        return 0

    ram = _ram_pct()
    if ram >= 80:
        print("RAM em %d%%: acima do orcamento (80%%). Nao vou indexar agora." % ram)
        return 2
    disp = a.dispositivo if a.dispositivo != "auto" else _dispositivo_auto()
    print("indexando %s -> %s  [%s, RAM %d%%]" % (pasta or biblioteca.PDFS, indice or biblioteca.INDICE, disp, ram))
    lilo_saiu = False
    if disp == "cuda" and not a.manter_lilo:
        lilo_saiu = _lilo_descarregar()
        print("lilo descarregado da GPU" if lilo_saiu else "lilo nao estava carregado (ou Ollama fora do ar)")
    t0 = time.time()
    try:
        st = biblioteca.indexar(pasta, indice, dispositivo=disp, limite=a.limite)
    finally:
        if lilo_saiu:
            print("aquecendo o lilo de novo...")
            _lilo_aquecer()
    print("fim: %d PDFs, %d novos (%d trechos), %d pulados, %d falhas em %.0f s" % (
        st["total"], st["novos"], st["trechos_novos"], st["pulados"], st["falhas"], time.time() - t0))
    return 0 if not st["falhas"] else 1


if __name__ == "__main__":
    sys.exit(main())
