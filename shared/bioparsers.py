"""
shared/bioparsers.py -- Parsers deterministicos de logs de bioinformatica (V20).

Transformam logs volumosos em uma TABELA COMPACTA (dado estruturado), em vez de
despejar o log bruto no contexto do Claude. Ganho tipico: ~3000 tokens de log
-> ~150 tokens de tabela. Python puro (stdlib), SEM LLM e SEM dependencias
novas -- extracao rapida e reproduzivel.

Formatos suportados (kind):
  - 'vina'   : log/pdbqt do AutoDock Vina -> afinidades (kcal/mol) + RMSD + melhor pose
  - 'qpcr'   : export de qPCR (csv/tsv/txt) -> Cq por amostra (+ eficiencia/R2/slope)
  - 'fastqc' : fastqc_data.txt ou summary.txt -> modulos PASS/WARN/FAIL
  - 'vcf'    : VCF -> contagens por tipo de variante, Ti/Tv, por cromossomo

Uso:
    from shared.bioparsers import parse_bio_log
    print(parse_bio_log("/caminho/vina.log"))        # kind='auto'
    print(parse_bio_log("/caminho/run.vcf", "vcf"))
"""
from __future__ import annotations

import re
from pathlib import Path

_SUPPORTED = ("vina", "qpcr", "fastqc", "vcf")


# ── Leitura tolerante (texto; .gz transparente) ──────────────────────────────
def _read(path: Path) -> str:
    if path.suffix.lower() == ".gz":
        import gzip
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    raw = path.read_bytes()
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ── Deteccao de formato ──────────────────────────────────────────────────────
def detect(path: Path, text: str) -> str:
    name = path.name.lower()
    head = text[:4000]
    if name.endswith((".vcf", ".vcf.gz")) or head.lstrip().startswith("##fileformat=VCF"):
        return "vcf"
    if "fastqc" in name or ">>Basic Statistics" in head or head.startswith("##FastQC"):
        return "fastqc"
    if ("AutoDock Vina" in head or "REMARK VINA RESULT" in text
            or re.search(r"affinity\s*\|?\s*\(?kcal", head, re.I)):
        return "vina"
    if re.search(r"\b(Cq|Ct)\b", head) and re.search(r"\b(Sample|Amostra|Well)\b", head, re.I):
        return "qpcr"
    return ""


# ── VINA ─────────────────────────────────────────────────────────────────────
def parse_vina(text: str) -> str:
    rows = []
    # (a) linhas de tabela do stdout: "   1       -9.2      0.000      0.000"
    for m in re.finditer(r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$",
                         text, re.M):
        rows.append((int(m.group(1)), float(m.group(2)),
                     float(m.group(3)), float(m.group(4))))
    # (b) REMARK VINA RESULT do(s) PDBQT de saida (sem numero de modo)
    if not rows:
        for i, m in enumerate(re.finditer(
                r"REMARK VINA RESULT:\s*(-?\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)", text), 1):
            rows.append((i, float(m.group(1)), float(m.group(2)), float(m.group(3))))
    if not rows:
        return "[vina] nenhuma tabela de afinidades reconhecida no arquivo."
    rows.sort(key=lambda r: r[0])
    best = min(rows, key=lambda r: r[1])
    lines = ["AutoDock Vina — %d pose(s). Melhor: modo %d = %.2f kcal/mol"
             % (len(rows), best[0], best[1]),
             "modo  affinity(kcal/mol)  rmsd_lb  rmsd_ub"]
    for mode, aff, lb, ub in rows[:20]:
        lines.append("%4d  %17.2f  %7.3f  %7.3f" % (mode, aff, lb, ub))
    if len(rows) > 20:
        lines.append("... (%d modos omitidos)" % (len(rows) - 20))
    return "\n".join(lines)


# ── qPCR ─────────────────────────────────────────────────────────────────────
def _sniff_delim(header: str) -> str:
    return max(("\t", ",", ";"), key=header.count)


def parse_qpcr(text: str) -> str:
    import csv, io, statistics as st
    lines = [ln for ln in text.splitlines() if ln.strip()]
    # localizar a linha de cabecalho (a que tem Cq/Ct)
    hidx = next((i for i, ln in enumerate(lines)
                 if re.search(r"\b(Cq|Ct|CT)\b", ln)), None)
    if hidx is None:
        return "[qpcr] cabecalho com coluna Cq/Ct nao encontrado."
    delim = _sniff_delim(lines[hidx])
    reader = list(csv.reader(io.StringIO("\n".join(lines[hidx:])), delimiter=delim))
    header = [h.strip() for h in reader[0]]

    def col(*names):
        # prioridade pela ORDEM dos aliases (nao pela ordem das colunas):
        # 'Sample' vence 'Well' mesmo que 'Well' apareca antes no cabecalho.
        for n in names:
            for i, h in enumerate(header):
                if re.fullmatch(n, h, re.I):
                    return i
        return None

    c_cq = col(r"Cq", r"Ct", r"CT", r"Cq Mean", r"Cq.?Mean")
    c_sample = col(r"Sample", r"Sample Name", r"Amostra", r"Well")
    c_target = col(r"Target", r"Target Name", r"Detector", r"Gene")
    if c_cq is None:
        return "[qpcr] coluna Cq/Ct nao localizada no cabecalho: %s" % header

    groups: dict[str, list[float]] = {}
    for row in reader[1:]:
        if len(row) <= c_cq:
            continue
        val = row[c_cq].strip()
        if not re.fullmatch(r"\d+(\.\d+)?", val):
            continue  # 'Undetermined', vazio, etc.
        key = []
        if c_sample is not None and len(row) > c_sample:
            key.append(row[c_sample].strip())
        if c_target is not None and len(row) > c_target:
            key.append(row[c_target].strip())
        groups.setdefault(" / ".join([k for k in key if k]) or "(sem nome)", []).append(float(val))

    if not groups:
        return "[qpcr] nenhum valor de Cq numerico encontrado."
    out = ["qPCR — %d grupo(s) amostra/alvo (Cq numerico):" % len(groups),
           "amostra/alvo                     n   Cq_medio  Cq_DP"]
    for name, vals in sorted(groups.items()):
        dp = st.pstdev(vals) if len(vals) > 1 else 0.0
        out.append("%-32s %3d  %8.2f  %5.2f" % (name[:32], len(vals),
                                                 st.mean(vals), dp))
    # parametros de curva-padrao, se presentes no texto livre
    curve = []
    for lab, pat in (("Eficiencia", r"[Ee]fficien\w*\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%?"),
                     ("R2", r"R\^?2\s*[:=]?\s*(\d\.\d+)"),
                     ("Slope", r"[Ss]lope\s*[:=]?\s*(-?\d+\.\d+)")):
        m = re.search(pat, text)
        if m:
            curve.append("%s=%s" % (lab, m.group(1)))
    if curve:
        out.append("Curva-padrao: " + ", ".join(curve))
    return "\n".join(out)


# ── FastQC ───────────────────────────────────────────────────────────────────
def parse_fastqc(text: str) -> str:
    mods = []
    # fastqc_data.txt: ">>Module name\tPASS|WARN|FAIL"
    for m in re.finditer(r"^>>(?!END_MODULE)(.+?)\t(pass|warn|fail)\s*$", text,
                         re.M | re.I):
        mods.append((m.group(1).strip(), m.group(2).upper()))
    # summary.txt: "PASS\tModule\tfile"
    if not mods:
        for m in re.finditer(r"^(PASS|WARN|FAIL)\t(.+?)\t", text, re.M | re.I):
            mods.append((m.group(2).strip(), m.group(1).upper()))
    if not mods:
        return "[fastqc] nenhum modulo PASS/WARN/FAIL reconhecido."
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for _, st_ in mods:
        counts[st_] = counts.get(st_, 0) + 1
    out = ["FastQC — %d modulos: %d PASS, %d WARN, %d FAIL"
           % (len(mods), counts["PASS"], counts["WARN"], counts["FAIL"])]
    for name, st_ in mods:
        flag = "" if st_ == "PASS" else "  <—"
        out.append("  %-5s %s%s" % (st_, name, flag))
    return "\n".join(out)


# ── VCF ──────────────────────────────────────────────────────────────────────
_TS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}


def parse_vcf_summary(text: str) -> str:
    total = snps = indels = ti = tv = 0
    by_chrom: dict[str, int] = {}
    for ln in text.splitlines():
        if not ln or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) < 5:
            continue
        chrom, ref, alts = f[0], f[3].upper(), f[4].upper()
        for alt in alts.split(","):
            if alt in (".", "<NON_REF>", "*"):
                continue
            total += 1
            by_chrom[chrom] = by_chrom.get(chrom, 0) + 1
            if len(ref) == 1 and len(alt) == 1:
                snps += 1
                if (ref, alt) in _TS:
                    ti += 1
                else:
                    tv += 1
            else:
                indels += 1
    if total == 0:
        return "[vcf] nenhuma variante encontrada (arquivo vazio ou so cabecalho)."
    titv = (ti / tv) if tv else float("nan")
    out = ["VCF — %d variantes: %d SNPs, %d indels" % (total, snps, indels),
           "Ti=%d  Tv=%d  Ti/Tv=%.2f" % (ti, tv, titv),
           "por cromossomo (top 15):"]
    for chrom, n in sorted(by_chrom.items(), key=lambda kv: -kv[1])[:15]:
        out.append("  %-10s %d" % (chrom, n))
    if len(by_chrom) > 15:
        out.append("  ... (%d cromossomos omitidos)" % (len(by_chrom) - 15))
    return "\n".join(out)


_PARSERS = {"vina": parse_vina, "qpcr": parse_qpcr,
            "fastqc": parse_fastqc, "vcf": parse_vcf_summary}


def parse_bio_log(path: str, kind: str = "auto") -> str:
    """Le um log de bioinformatica local e devolve uma TABELA COMPACTA.

    O log bruto nao entra no contexto do Claude -- so a tabela destilada.

    Args:
        path: caminho do log local.
        kind: 'auto' (detecta) | 'vina' | 'qpcr' | 'fastqc' | 'vcf'.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"[parse_bio_log] Arquivo nao encontrado: {path}"
    if p.is_dir():
        return f"[parse_bio_log] E um diretorio, nao um arquivo: {path}"
    try:
        text = _read(p)
    except Exception as e:  # noqa: BLE001
        return f"[parse_bio_log] Erro ao ler {p.name}: {e}"

    k = (kind or "auto").lower()
    if k == "auto":
        k = detect(p, text)
        if not k:
            return ("[parse_bio_log] Formato nao reconhecido automaticamente. "
                    "Informe kind=vina|qpcr|fastqc|vcf, ou use lilo_summarize_file "
                    "para um resumo generico.")
    if k not in _PARSERS:
        return f"[parse_bio_log] kind invalido: {k}. Suportados: {', '.join(_SUPPORTED)}."
    try:
        return _PARSERS[k](text)
    except Exception as e:  # noqa: BLE001
        return f"[parse_bio_log] Erro ao parsear ({k}) {p.name}: {e}"
