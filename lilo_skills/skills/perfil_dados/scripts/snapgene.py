#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapgene.py — Lê o mapa de um plasmídeo SnapGene (.dna, binário) sem despejar o
binário nem a sequência inteira no contexto.

Formato (verificado): série de segmentos [1 byte tipo][4 bytes uint32 BE len][payload].
  0x00 DNA-seq   -> payload[0]=flags (bit0 circular, bit1 dupla-fita, bit2 dam,
                    bit3 dcm, bit4 EcoKI); payload[1:]=sequência ASCII
  0x05 Primers   -> XML
  0x06 Notes     -> XML
  0x0A Features   -> XML (<Feature name= type=><Segment range="a-b"/></Feature>)
  0x09 Cookie    -> "SnapGene"

Saída padrão: mapa compacto (nome, tamanho, topologia, %GC, features, primers,
notas) em texto ou JSON. A sequência completa só sai com --seq.

Uso:
  python snapgene.py ARQ.dna [--json] [--seq] [--fasta SAIDA.fasta]
"""
from __future__ import annotations
import argparse
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _segments(data: bytes):
    pos, n = 0, len(data)
    while pos + 5 <= n:
        t = data[pos]
        ln = struct.unpack_from(">I", data, pos + 1)[0]
        payload = data[pos + 5: pos + 5 + ln]
        if len(payload) < ln:  # truncado
            break
        yield t, payload
        pos += 5 + ln


def _parse_features(xml_bytes: bytes):
    feats = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return feats
    for f in root.iter():
        if f.tag.rsplit("}", 1)[-1] != "Feature":
            continue
        name = f.get("name", "")
        ftype = f.get("type", "")
        ranges = []
        for seg in f:
            if seg.tag.rsplit("}", 1)[-1] == "Segment":
                r = seg.get("range", "")
                m = re.match(r"(\d+)\s*-\s*(\d+)", r or "")
                if m:
                    ranges.append((int(m.group(1)), int(m.group(2))))
        # 1º início / último fim NA ORDEM dos segmentos (não min/max): features de
        # plasmídeo circular cruzam a origem (fim < início), e min/max descartaria
        # silenciosamente a metade que passa pelo ponto zero.
        if ranges:
            inicio, fim = ranges[0][0], ranges[-1][1]
            cruza_origem = fim < inicio or any(b < a for a, b in ranges)
        else:
            inicio = fim = None
            cruza_origem = False
        feats.append({"nome": name, "tipo": ftype, "inicio": inicio, "fim": fim,
                      "cruza_origem": cruza_origem})
    return feats


def _parse_primers(xml_bytes: bytes):
    prims = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return prims
    for p in root.iter():
        if p.tag.rsplit("}", 1)[-1] == "Primer":
            prims.append({"nome": p.get("name", ""), "seq": (p.get("sequence", "") or "")[:60]})
    return prims


def _notes_text(xml_bytes: bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {}
    out = {}
    for ch in root:
        tag = ch.tag.rsplit("}", 1)[-1]
        if ch.text and ch.text.strip():
            out[tag] = ch.text.strip()[:200]
    return out


def parse_dna(path: Path):
    data = path.read_bytes()
    # cookie completo 0x09 + uint32(14) + "SnapGene"; checar só o 1º byte (0x09=TAB)
    # aceitaria por engano TSV/textos iniciados por tabulação.
    if len(data) < 13 or data[0] != 0x09 or data[5:13] != b"SnapGene":
        raise ValueError("não parece um arquivo SnapGene .dna (cookie 'SnapGene' ausente)")
    info = {"arquivo": path.name, "MB": round(len(data) / 1e6, 3),
            "seq_len": 0, "topologia": "?", "GC_pct": None,
            "features": [], "primers": [], "notas": {}}
    seq = ""
    for t, payload in _segments(data):
        if t == 0x00 and payload:
            flags = payload[0]
            seq = payload[1:].decode("ascii", "replace")
            info["seq_len"] = len(seq)
            info["topologia"] = "circular" if (flags & 0x01) else "linear"
            info["fita"] = "dupla" if (flags & 0x02) else "simples"
            gc = sum(1 for c in seq if c in "GCgc")
            info["GC_pct"] = round(100 * gc / len(seq), 1) if seq else None
        elif t == 0x0A:
            info["features"] = _parse_features(payload)
        elif t == 0x05:
            info["primers"] = _parse_primers(payload)
        elif t == 0x06:
            info["notas"] = _notes_text(payload)
    return info, seq


def report_txt(info):
    L = [f"# Mapa SnapGene — {info['arquivo']}", "",
         f"- Tamanho: **{info['seq_len']} pb** · {info.get('topologia','?')} · "
         f"fita {info.get('fita','?')} · GC {info.get('GC_pct','?')}%",
         f"- Binário: {info['MB']} MB · {len(info['features'])} features · "
         f"{len(info['primers'])} primers"]
    if info.get("notas"):
        L.append("- Notas: " + "; ".join(f"{k}={v}" for k, v in info["notas"].items()))
    if info["features"]:
        L += ["", f"## Features ({len(info['features'])})",
              "| # | Nome | Tipo | Início | Fim |", "|--:|---|---|--:|--:|"]
        tem_circular = False
        for i, f in enumerate(info["features"], 1):
            obs = " ↻" if f.get("cruza_origem") else ""
            tem_circular = tem_circular or f.get("cruza_origem")
            L.append(f"| {i} | {f['nome']} | {f['tipo']} | {f['inicio']} | {f['fim']}{obs} |")
        if tem_circular:
            L.append("\n↻ = feature cruza a origem do plasmídeo circular (fim < início); "
                     "o comprimento **não** é fim−início.")
    if info["primers"]:
        L += ["", f"## Primers ({len(info['primers'])})"]
        for p in info["primers"]:
            L.append(f"- {p['nome']}: `{p['seq']}`")
    return "\n".join(L)


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Lê o mapa de um plasmídeo SnapGene .dna (sem despejar o binário).")
    ap.add_argument("arquivo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--seq", action="store_true", help="também imprime a sequência completa")
    ap.add_argument("--fasta", help="grava a sequência em FASTA")
    a = ap.parse_args(argv)

    info, seq = parse_dna(Path(a.arquivo))
    if a.fasta:
        Path(a.fasta).write_text(f">{Path(a.arquivo).stem}\n{seq}\n", encoding="utf-8")
        print(f"[snapgene] FASTA gravado: {a.fasta} ({len(seq)} pb)", file=sys.stderr)
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(report_txt(info))
        if a.seq:
            print("\n## Sequência\n" + seq)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
