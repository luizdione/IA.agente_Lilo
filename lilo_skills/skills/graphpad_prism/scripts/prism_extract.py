#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prism_extract.py — Extrator de arquivos do GraphPad Prism (.pzfx / .pzf / .pzt).

Dois motores, escolhidos automaticamente pela assinatura do arquivo:

  1) .pzfx / .pzt  -> XML do Prism (Prism 5+). Parsing FIEL:
       - tabelas de dados (rótulos de linha + colunas Y com réplicas/subcolunas) -> CSV
       - metadados de projeto (Info/Constant) -> info.json
       - tabelas de resultados de análise (quando presentes como <Table>) -> CSV

  2) .pzf com assinatura "PCFFGRA4" -> binário legado (Prism 4). Extração BEST-EFFORT:
       - texto UTF-16 (fonte primária) + ASCII, filtrado de ruído -> stream lógico
       - reconstrução heurística de tabelas (rótulos + colunas numéricas) -> CSV
       - nomes de análises e blocos "Tabular/Narrative results" -> resultados.txt
       - figuras embutidas (Enhanced Metafile / EMF) carvadas por assinatura -> figuras/*.emf

Saída: <outdir>/ com subpastas tabelas/, figuras/, e os arquivos
inventario.json, resultados.txt e RELATORIO.md.

Uso:
  python prism_extract.py ARQUIVO [--outdir DIR] [--no-figuras] [--quiet]

Sem dependências obrigatórias (só stdlib). pandas é usado se disponível
(fallback para csv puro caso contrário).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ------------------------------------------------------------------ util

def _log(msg, quiet=False):
    if not quiet:
        print(msg, file=sys.stderr)

def _slug(s, maxlen=60):
    s = re.sub(r"[^\w\-.() ]+", "_", (s or "").strip())
    s = re.sub(r"\s+", "_", s).strip("_.") or "sem_titulo"
    return s[:maxlen]

def _write_csv(path, header, rows):
    """Grava CSV (usa pandas se houver, senão csv stdlib)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd  # noqa
        df = pd.DataFrame(rows, columns=header if header else None)
        df.to_csv(path, index=False, encoding="utf-8-sig")
    except Exception:
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            if header:
                w.writerow(header)
            w.writerows(rows)
    return path

# ------------------------------------------------------------------ detecção

def detect_format(data: bytes) -> str:
    head = data[:512]
    if head[:8] == b"PCFFGRA4":
        return "pzf_binary"
    # pzfx/pzt são XML (podem ter BOM ou espaços iniciais)
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped[:5] == b"<?xml" or b"GraphPadPrismFile" in head:
        return "pzfx_xml"
    if stripped[:2] == b"PK":
        return "zip"  # pzfx raramente zipado; sinaliza para o usuário
    return "unknown"

# ------------------------------------------------------------------ motor XML (.pzfx)

def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def _localname_iter(root):
    for el in root.iter():
        yield el, _strip_ns(el.tag)

def _text(el):
    return (el.text or "").strip() if el is not None else ""

def _subcolumn_values(sub):
    """Lê os <d> de um <Subcolumn>. Vazio/ausente -> '' ; Excluded marcado com sufixo."""
    vals = []
    for d in sub:
        if _strip_ns(d.tag) != "d":
            continue
        v = (d.text or "").strip()
        if d.get("Excluded") in ("1", "true", "True"):
            v = f"{v} [EXCLUÍDO]" if v else "[EXCLUÍDO]"
        vals.append(v)
    return vals

def parse_pzfx(data: bytes, outdir: Path, want_figs=True, quiet=False) -> dict:
    inv = {"formato": "pzfx_xml", "tabelas": [], "info": {}, "avisos": []}
    text = data.decode("utf-8", "replace")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        # tentativa: cortar lixo antes do primeiro '<'
        i = text.find("<?xml")
        if i < 0:
            i = text.find("<GraphPadPrismFile")
        root = ET.fromstring(text[i:]) if i >= 0 else None
        if root is None:
            inv["avisos"].append(f"XML inválido: {e}")
            return inv

    # ---- Info / Constant (metadados do projeto)
    for info in root.iter():
        if _strip_ns(info.tag) != "Info":
            continue
        title = ""
        consts = {}
        for ch in info:
            ln = _strip_ns(ch.tag)
            if ln == "Title":
                title = _text(ch)
            elif ln == "Constant":
                name = val = ""
                for c in ch:
                    if _strip_ns(c.tag) == "Name":
                        name = _text(c)
                    elif _strip_ns(c.tag) == "Value":
                        val = _text(c)
                if name:
                    consts[name] = val
        if title or consts:
            inv["info"][title or f"Info_{len(inv['info'])}"] = consts

    # ---- Tabelas
    tdir = outdir / "tabelas"
    n = 0
    for tbl in root.iter():
        if _strip_ns(tbl.tag) != "Table":
            continue
        n += 1
        title = ""
        ttype = tbl.get("TableType", "")
        for ch in tbl:
            if _strip_ns(ch.tag) == "Title":
                title = _text(ch)
                break
        title = title or f"Tabela_{n}"

        # coluna de rótulos de linha
        row_titles = []
        for ch in tbl:
            if _strip_ns(ch.tag) == "RowTitlesColumn":
                for sub in ch:
                    if _strip_ns(sub.tag) == "Subcolumn":
                        row_titles = _subcolumn_values(sub)
                        break

        # colunas (X e Y) -> lista de (header, valores)
        columns = []
        for ch in tbl:
            ln = _strip_ns(ch.tag)
            if ln not in ("XColumn", "YColumn", "XAdvancedColumn"):
                continue
            col_title = ""
            for c in ch:
                if _strip_ns(c.tag) == "Title":
                    col_title = _text(c)
                    break
            col_title = col_title or ("X" if ln.startswith("X") else f"Y{len([x for x in columns])+1}")
            subs = [s for s in ch if _strip_ns(s.tag) == "Subcolumn"]
            if len(subs) <= 1:
                vals = _subcolumn_values(subs[0]) if subs else []
                columns.append((col_title, vals))
            else:
                for si, s in enumerate(subs, 1):
                    columns.append((f"{col_title}_rep{si}", _subcolumn_values(s)))

        # monta matriz por linhas
        maxrows = max([len(row_titles)] + [len(v) for _, v in columns] + [0])
        header = (["Linha"] if row_titles else []) + [h for h, _ in columns]
        rows = []
        for r in range(maxrows):
            row = ([row_titles[r] if r < len(row_titles) else ""] if row_titles else [])
            for _, v in columns:
                row.append(v[r] if r < len(v) else "")
            rows.append(row)

        fname = f"{n:02d}_{_slug(title)}.csv"
        _write_csv(tdir / fname, header, rows)
        inv["tabelas"].append({
            "n": n, "titulo": title, "tipo": ttype,
            "linhas": maxrows, "colunas": len(header), "csv": f"tabelas/{fname}",
        })
        _log(f"  [pzfx] tabela {n}: {title!r} ({maxrows}x{len(header)}) -> {fname}", quiet)

    return inv

# ------------------------------------------------------------------ motor binário (.pzf PCFFGRA4)

_NOISE = {
    "Arial", "Symbol", "Wingdings", "MS Sans Serif", "Times New Roman",
    "winsp", "EMF", "ngdings", "Courier New", "Tahoma", "Calibri",
}
_NUM_RE = re.compile(r"^-?\d+(?:[.,]\d+)?(?:[eE]-?\d+)?%?$")
_ANALYSIS_HINT = re.compile(
    r"ANOVA|t test|t-test|regress|correlat|survival|contingency|chi|"
    r"Tabular results|Narrative results|column stat|nonlinear|Kruskal|"
    r"Mann-Whitney|Wilcoxon|Dunn|Tukey|Bonferroni|Sidak|post test|"
    r"R square|P value|p value|Difference|95% CI|SEM|SD\b|Mean",
    re.I,
)

def _harvest_runs(data: bytes):
    """Colhe runs UTF-16LE (primário) e ASCII, com offset. Retorna [(off, kind, text)]."""
    runs = []
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){2,}", data):
        runs.append((m.start(), "u16", m.group().decode("utf-16-le", "replace").strip()))
    for m in re.finditer(rb"[\x20-\x7e]{3,}", data):
        runs.append((m.start(), "asc", m.group().decode("latin-1").strip()))
    runs.sort(key=lambda t: t[0])
    return runs

def _is_repeat_noise(s: str) -> bool:
    # descarta runs de 3 chars repetidos (dados de bitmap dentro de EMF: "ppp","fff"...)
    if len(s) <= 4 and re.fullmatch(r"(.)\1{2,}", s):
        return True
    if re.fullmatch(r"[a-z]{3}", s):  # 'ppp','uuu' etc.
        return True
    return False

def find_emf_blocks(data: bytes):
    """Localiza Enhanced Metafiles embutidos pela assinatura ' EMF' (0x20454D46)
    no offset +40 do ENHMETAHEADER (iType==1). Retorna [(start, nBytes)]."""
    out = []
    N = len(data)
    for m in re.finditer(b"\x20\x45\x4d\x46", data):
        hdr = m.start() - 40
        if hdr < 0:
            continue
        try:
            iType = struct.unpack_from("<I", data, hdr)[0]
            nBytes = struct.unpack_from("<I", data, hdr + 48)[0]
        except struct.error:
            continue
        if iType == 1 and 88 <= nBytes <= N:
            out.append((hdr, nBytes))
    return out

def _carve_emf(data: bytes, start: int, declared_nbytes: int) -> bytes:
    """Carva um EMF de `start` até o registro EMR_EOF (iType==14), respeitando
    o nBytes declarado como teto. Mais robusto que confiar só no nBytes."""
    N = len(data)
    end_cap = min(start + declared_nbytes, N)
    pos = start
    # percorre registros: cada um = <iType u32><nSize u32> ...
    last = end_cap
    while pos + 8 <= N and pos < end_cap:
        try:
            iType, nSize = struct.unpack_from("<II", data, pos)
        except struct.error:
            break
        if nSize < 8 or nSize > (end_cap - pos) + 4096:
            break
        pos += nSize
        if iType == 14:  # EMR_EOF
            last = pos
            break
    return data[start:min(last, end_cap)]

def parse_pzf_binary(data: bytes, outdir: Path, want_figs=True, quiet=False) -> dict:
    inv = {"formato": "pzf_binary_PCFFGRA4", "tabelas": [], "analises": [],
           "figuras": [], "info": {}, "avisos": [
               "Formato binário legado (Prism 4): extração é BEST-EFFORT. "
               "Para fidelidade total, reexporte do Prism como .pzfx (XML) ou CSV."]}

    runs = _harvest_runs(data)
    # stream limpo: remove ruído e duplicatas óbvias mantendo ordem
    clean = []
    for off, kind, val in runs:
        if not val or val in _NOISE or _is_repeat_noise(val):
            continue
        clean.append((off, kind, val))

    # metadados simples (impressora/data às vezes aparecem no cabeçalho)
    for off, kind, val in clean[:20]:
        if re.search(r"printer|series|LaserJet|Photosmart|Deskjet", val, re.I):
            inv["info"].setdefault("dispositivo_impressao", val)

    # nomes de análises / blocos de resultados
    seen_analysis = set()
    for off, kind, val in clean:
        if _ANALYSIS_HINT.search(val) and val not in seen_analysis and len(val) > 3:
            # ignora tokens muito curtos que só batem "SD"/"Mean" isolados repetidos
            seen_analysis.add(val)
            inv["analises"].append({"offset": off, "texto": val})

    # ---- reconstrução heurística de tabelas
    # agrupa runs UTF-16 por proximidade de offset; dentro de cada grupo,
    # separa rótulos (texto) de valores (numéricos) em ordem.
    u16 = [(o, v) for o, k, v in clean if k == "u16"]
    groups = []
    cur = []
    GAP = 2048  # bytes: novo grupo quando há salto grande de offset
    last_off = None
    for o, v in u16:
        if last_off is not None and (o - last_off) > GAP and cur:
            groups.append(cur); cur = []
        cur.append((o, v)); last_off = o
    if cur:
        groups.append(cur)

    tdir = outdir / "tabelas"
    tno = 0
    for g in groups:
        labels = [v for _, v in g if not _NUM_RE.match(v) and 1 <= len(v) <= 40]
        nums = [v for _, v in g if _NUM_RE.match(v)]
        if len(nums) < 3:  # grupo sem massa numérica: provavelmente legenda/título
            continue
        tno += 1
        title = next((v for _, v in g if not _NUM_RE.match(v) and len(v) > 4),
                     f"bloco_{tno}")
        # CSV simples de 2 colunas: rótulo_aproximado | valor (ordem de ocorrência)
        header = ["rotulo_ou_contexto", "valor"]
        rows = []
        pending_label = ""
        for _, v in g:
            if _NUM_RE.match(v):
                rows.append([pending_label, v])
            else:
                pending_label = v
        fname = f"{tno:02d}_{_slug(title)}.csv"
        _write_csv(tdir / fname, header, rows)
        inv["tabelas"].append({
            "n": tno, "titulo_aprox": title, "n_valores": len(nums),
            "n_rotulos": len(labels), "csv": f"tabelas/{fname}",
            "confianca": "best-effort",
        })
        _log(f"  [pzf] bloco {tno}: {title!r} ({len(nums)} valores) -> {fname}", quiet)

    # ---- figuras EMF
    # O Prism guarda cada gráfico como um par de EMFs consecutivos de MESMO tamanho
    # (versão tela + versão impressão; não são byte-idênticos). Deduplica-se por
    # nBytes consecutivo igual, ficando com a 1ª ocorrência. Descartam-se blobs
    # minúsculos (< MIN_EMF), que são thumbnails/artefatos, não gráficos reais.
    MIN_EMF = 1024
    if want_figs:
        fdir = outdir / "figuras"
        blocks = find_emf_blocks(data)
        fno = 0
        descartadas_pares = 0
        prev_nb = None
        for start, nb in blocks:
            if prev_nb is not None and nb == prev_nb:
                # 2º EMF do par tela/impressão do gráfico anterior -> ignora.
                # RESET (prev_nb=None) para NÃO colapsar um 3º gráfico distinto de
                # mesmo tamanho: o pareamento é por dupla (toggle), não por run.
                prev_nb = None
                descartadas_pares += 1
                continue
            prev_nb = nb
            blob = _carve_emf(data, start, nb)
            if len(blob) < MIN_EMF:
                continue
            fno += 1
            fp = fdir / f"figura_{fno:02d}.emf"
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(blob)
            inv["figuras"].append({"n": fno, "arquivo": f"figuras/figura_{fno:02d}.emf",
                                    "bytes": len(blob), "offset": start})
            _log(f"  [pzf] figura {fno}: {len(blob)} bytes -> figura_{fno:02d}.emf", quiet)
        if fno:
            inv["avisos"].append(
                f"{fno} figura(s) salvas como .emf vetorial "
                f"(descartados {descartadas_pares} pares tela/impressão e blobs <1KB). "
                "Converta com scripts/emf_convert.py para PNG/SVG/PDF.")

    return inv


def _reflow_result(s: str) -> str:
    """Insere quebras de linha em blocos longos de resultado do Prism para
    torná-los legíveis, sem alterar os números."""
    if len(s) < 160:
        return s
    # quebra antes de marcadores estruturais frequentes na saída do Prism
    for mark in ("Does ", "The P value", "If there is no", "If RNAi", "If Tempo",
                 "If time", "If matching", "Was the matching", "Table Analyzed",
                 "Source of Variation", "Bonferroni", "Number of ", "P value summary",
                 "95% CI", "Significant?", "Sum-of-squares", "Mean square", "Summary"):
        s = s.replace(mark, "\n  " + mark)
    return s.strip()

# ------------------------------------------------------------------ relatório

def write_report(inv: dict, src: Path, outdir: Path):
    md = [f"# Extração do Prism — `{src.name}`", ""]
    md.append(f"- **Formato detectado:** `{inv.get('formato')}`")
    md.append(f"- **Origem:** `{src}`")
    md.append(f"- **Saída:** `{outdir}`")
    md.append("")
    if inv.get("info"):
        md.append("## Metadados do projeto")
        for k, v in inv["info"].items():
            if isinstance(v, dict):
                md.append(f"- **{k}**")
                for kk, vv in v.items():
                    md.append(f"    - {kk}: {vv}")
            else:
                md.append(f"- **{k}:** {v}")
        md.append("")
    if inv.get("tabelas"):
        md.append(f"## Tabelas extraídas ({len(inv['tabelas'])})")
        for t in inv["tabelas"]:
            tit = t.get("titulo") or t.get("titulo_aprox")
            extra = f" · {t.get('linhas','?')}×{t.get('colunas','?')}" if "linhas" in t else \
                    f" · {t.get('n_valores','?')} valores ({t.get('confianca','')})"
            md.append(f"- **{tit}**{extra} → `{t['csv']}`")
        md.append("")
    if inv.get("analises"):
        md.append(f"## Análises detectadas ({len(inv['analises'])})")
        for a in inv["analises"][:40]:
            md.append(f"- {a['texto']}")
        md.append("")
    if inv.get("figuras"):
        md.append(f"## Figuras (EMF vetorial) ({len(inv['figuras'])})")
        for f in inv["figuras"]:
            md.append(f"- `{f['arquivo']}` ({f['bytes']} bytes)")
        md.append("")
    if inv.get("avisos"):
        md.append("## Avisos")
        for w in inv["avisos"]:
            md.append(f"- {w}")
        md.append("")
    (outdir / "RELATORIO.md").write_text("\n".join(md), encoding="utf-8")

    # resultados.txt (nomes de análises + qualquer texto de resultado, reflow legível)
    if inv.get("analises"):
        lines = [f"# Análises e resultados detectados em {src.name}",
                 "# (extração best-effort do binário; confira contra o Prism)", ""]
        for a in inv["analises"]:
            lines.append(f"[offset {a.get('offset','?')}] {_reflow_result(a['texto'])}")
            lines.append("")
        (outdir / "resultados.txt").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------ main

def extract(src: str, outdir: str | None = None, want_figs=True, quiet=False) -> dict:
    src = Path(src)
    data = src.read_bytes()
    fmt = detect_format(data)
    if outdir is None:
        outdir = src.with_name(src.stem + "_extração")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    _log(f"[prism_extract] {src.name} → formato: {fmt}", quiet)
    if fmt == "pzfx_xml":
        inv = parse_pzfx(data, outdir, want_figs, quiet)
    elif fmt == "pzf_binary":
        inv = parse_pzf_binary(data, outdir, want_figs, quiet)
    elif fmt == "zip":
        inv = {"formato": "zip", "avisos": [
            "Arquivo parece ZIP. Descompacte e procure o .xml/.pzfx interno, "
            "ou reexporte do Prism como .pzfx não compactado."]}
    else:
        inv = {"formato": "unknown", "avisos": [
            "Assinatura não reconhecida. Abra no GraphPad Prism e use "
            "File > Export ou Save As para gerar .pzfx (XML) ou CSV."]}

    inv["_origem"] = str(src)
    inv["_saida"] = str(outdir)
    (outdir / "inventario.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(inv, src, outdir)
    _log(f"[prism_extract] concluído → {outdir}", quiet)
    return inv

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extrai dados, resultados e figuras de arquivos GraphPad Prism (.pzfx/.pzf).")
    ap.add_argument("arquivo", help="caminho do .pzfx ou .pzf")
    ap.add_argument("--outdir", default=None, help="pasta de saída (default: <nome>_extração)")
    ap.add_argument("--no-figuras", action="store_true", help="não extrair figuras EMF")
    ap.add_argument("--quiet", action="store_true", help="silencioso")
    a = ap.parse_args(argv)
    inv = extract(a.arquivo, a.outdir, want_figs=not a.no_figuras, quiet=a.quiet)
    # resumo em stdout (JSON) para uso programático
    resumo = {k: inv[k] for k in ("formato", "_saida") if k in inv}
    resumo["n_tabelas"] = len(inv.get("tabelas", []))
    resumo["n_analises"] = len(inv.get("analises", []))
    resumo["n_figuras"] = len(inv.get("figuras", []))
    # ensure_ascii=True (default): evita UnicodeEncodeError no stdout quando o
    # caminho tem acento (ex. "_extração") e o console é ASCII/PYTHONIOENCODING=ascii.
    print(json.dumps(resumo))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
