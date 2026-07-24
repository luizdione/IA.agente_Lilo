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

NOTA DE PRECISAO (V20.1, apos auditoria adversarial): estes parsers substituem o
log bruto no contexto -- o usuario NAO ve mais o original. Portanto qualquer
descarte silencioso de linha e um erro de DADO CIENTIFICO. As regexes aceitam
numeros com/sem casa decimal e virgula decimal (pt-BR), e o parser AVISA quando a
numeracao de poses tem lacuna, em vez de reportar um "melhor" que nao e o melhor.
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
    parent = path.parent.name.lower()
    head = text[:4000]
    if name.endswith((".vcf", ".vcf.gz")) or head.lstrip().startswith("##fileformat=VCF"):
        return "vcf"
    # FastQC: fastqc_data.txt, summary.txt (dentro de *_fastqc/), ou assinatura.
    if ("fastqc" in name or "fastqc" in parent
            or ">>Basic Statistics" in head or head.startswith("##FastQC")
            or re.search(r"^(PASS|WARN|FAIL)\t\S[^\t]*\t", head, re.M)):
        return "fastqc"
    # Vina: ancorar na ESTRUTURA da tabela (nao em 'affinity' solto, que aparece
    # em CSVs de docking e geraria falso-positivo).
    if ("REMARK VINA RESULT" in text
            or re.search(r"^\s*mode\s*\|\s*affinity\b", head, re.I | re.M)
            or re.search(r"\(kcal/mol\)\s*\|\s*rmsd", head, re.I)):
        return "vina"
    if re.search(r"\b(Cq|Ct)\b", head) and re.search(r"\b(Sample|Amostra|Well)\b", head, re.I):
        return "qpcr"
    return ""


# ── VINA ─────────────────────────────────────────────────────────────────────
# Casa uma linha INTEIRA da tabela. Casa decimal OPCIONAL: o Vina 1.2.x imprime
# os RMSD do modo 1 como "0" (defaultfloat, sem std::fixed), nao "0.000" -- com
# decimal obrigatorio a MELHOR POSE era descartada em silencio. [^\S\r\n] = espaco
# que NAO inclui quebra de linha (impede montar 'pose' com numeros de linhas
# diferentes).
_VINA_ROW = re.compile(
    r"[^\S\r\n]*(\d+)[^\S\r\n]+(-?\d+(?:\.\d+)?)[^\S\r\n]+(\d+(?:\.\d+)?)[^\S\r\n]+(\d+(?:\.\d+)?)[^\S\r\n]*")
_VINA_SEP = re.compile(r"^[-+\s]*-{3,}\+[-+\s]*$", re.M)
_VINA_REMARK = re.compile(
    r"REMARK VINA RESULT:\s*(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)")


def parse_vina(text: str) -> str:
    rows = []
    # Ancorar no corpo da tabela (apos a linha separadora "-----+------+-----"),
    # para compensar o relaxamento da regex e evitar casar "1 2 3 4" solto.
    body = text
    m_sep = _VINA_SEP.search(text)
    if m_sep:
        body = text[m_sep.end():]
    for ln in body.splitlines():
        m = _VINA_ROW.fullmatch(ln)
        if m:
            rows.append((int(m.group(1)), float(m.group(2)),
                         float(m.group(3)), float(m.group(4))))
    # (b) REMARK VINA RESULT dos PDBQT de saida (sem numero de modo).
    if not rows:
        for i, m in enumerate(_VINA_REMARK.finditer(text), 1):
            rows.append((i, float(m.group(1)), float(m.group(2)), float(m.group(3))))
    if not rows:
        return "[vina] nenhuma tabela de afinidades reconhecida no arquivo."

    rows.sort(key=lambda r: r[0])
    best = min(rows, key=lambda r: r[1])
    out = []
    # Defesa contra descarte silencioso: se a numeracao nao for 1..N contigua,
    # alguma linha nao foi reconhecida -> avisar em vez de mentir sobre a melhor pose.
    modos = [r[0] for r in rows]
    if modos[0] != 1 or modos != list(range(modos[0], modos[0] + len(modos))):
        out.append("[vina] AVISO: numeracao de modos com lacuna (%s) -- alguma linha "
                   "nao foi reconhecida; a 'melhor pose' pode nao ser a real."
                   % ", ".join(str(m) for m in modos[:12]))
    out.append("AutoDock Vina — %d pose(s). Melhor: modo %d = %.2f kcal/mol"
               % (len(rows), best[0], best[1]))
    out.append("modo  affinity(kcal/mol)  rmsd_lb  rmsd_ub")
    for mode, aff, lb, ub in rows[:20]:
        out.append("%4d  %17.2f  %7.3f  %7.3f" % (mode, aff, lb, ub))
    if len(rows) > 20:
        out.append("... (%d modos omitidos)" % (len(rows) - 20))
    return "\n".join(out)


# ── qPCR ─────────────────────────────────────────────────────────────────────
# Cabecalho valido = linha DELIMITADA com um CAMPO exatamente Cq/Ct (+/- 'Mean').
# Evita que o preambulo de ABI/QuantStudio ("Comparative CT", texto livre)
# sequestre a deteccao e derrube o parser inteiro.
_CQ_HDR = re.compile(r"(Cq|Ct)([ _.\-]?Mean)?", re.I)
# Cq com ponto OU virgula (exports pt-BR: CFX Maestro / LightCycler / Excel).
_CQ_VAL = re.compile(r"\d+([.,]\d+)?")


def _find_header(lines: list[str]):
    """Devolve (indice, delimitador) do 1o cabecalho DELIMITADO com coluna Cq/Ct."""
    for i, ln in enumerate(lines):
        for delim in ("\t", ",", ";"):
            if delim not in ln:
                continue
            campos = [c.strip().strip('"') for c in ln.split(delim)]
            if any(_CQ_HDR.fullmatch(c) for c in campos):
                return i, delim
    return None, None


def parse_qpcr(text: str) -> str:
    import csv, io, statistics as st
    lines = [ln for ln in text.splitlines() if ln.strip()]
    hidx, delim = _find_header(lines)
    if hidx is None:
        return "[qpcr] cabecalho delimitado com coluna Cq/Ct nao encontrado."
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

    c_cq = col(r"Cq", r"Ct", r"CT", r"Cq[ _.\-]?Mean", r"Ct[ _.\-]?Mean")
    c_sample = col(r"Sample", r"Sample Name", r"Amostra", r"Well")
    c_target = col(r"Target", r"Target Name", r"Detector", r"Gene")
    if c_cq is None:
        return "[qpcr] coluna Cq/Ct nao localizada no cabecalho: %s" % header

    groups: dict[str, list[float]] = {}
    descartados = 0
    for row in reader[1:]:
        if len(row) <= c_cq:
            continue
        val = row[c_cq].strip().strip('"')
        if not _CQ_VAL.fullmatch(val):
            descartados += 1  # 'Undetermined', 'N/A', vazio
            continue
        key = []
        if c_sample is not None and len(row) > c_sample:
            key.append(row[c_sample].strip())
        if c_target is not None and len(row) > c_target:
            key.append(row[c_target].strip())
        name = " / ".join([k for k in key if k]) or "(sem nome)"
        groups.setdefault(name, []).append(float(val.replace(",", ".")))

    if not groups:
        return ("[qpcr] nenhum valor de Cq numerico encontrado "
                "(%d celula(s) nao-numerica(s), ex.: 'Undetermined')." % descartados)
    out = ["qPCR — %d grupo(s) amostra/alvo (Cq numerico):" % len(groups),
           "amostra/alvo                     n   Cq_medio  Cq_SD"]
    for name, vals in sorted(groups.items()):
        # SD AMOSTRAL (n-1), como MIQE/CFX/QuantStudio reportam.
        sd = st.stdev(vals) if len(vals) > 1 else 0.0
        out.append("%-32s %3d  %8.2f  %5.2f" % (name[:32], len(vals),
                                                st.mean(vals), sd))
    if descartados:
        out.append("(%d celula(s) nao-numerica(s) descartada(s), ex.: 'Undetermined')"
                   % descartados)
    # parametros de curva-padrao, se presentes no texto livre
    curve = []
    for lab, pat in (("Eficiencia", r"[Ee]fficien\w*\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%?"),
                     ("R2", r"R\^?2\s*[:=]?\s*(\d[.,]\d+)"),
                     ("Slope", r"[Ss]lope\s*[:=]?\s*(-?\d+[.,]\d+)")):
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
# Alelos NAO-variantes: gVCF (GATK <NON_REF>, bcftools <*>) e o 'resto' '*'.
_NONVAR_ALT = {".", "*", "<NON_REF>", "<*>"}
_ACGT = set("ACGTN")


def parse_vcf_summary(text: str) -> str:
    total = snps = indels = svs = ti = tv = 0
    nonvar = 0
    by_chrom: dict[str, int] = {}
    for ln in text.splitlines():
        if not ln or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) < 5:
            continue
        chrom, ref, alts = f[0], f[3].upper().strip(), f[4].upper().strip()
        for alt in alts.split(","):
            alt = alt.strip()
            if not alt or alt in _NONVAR_ALT:
                nonvar += 1          # gVCF: linha de referencia, NAO e variante
                continue
            total += 1
            by_chrom[chrom] = by_chrom.get(chrom, 0) + 1
            if alt.startswith("<") or "[" in alt or "]" in alt:
                svs += 1             # simbolico (<DEL>/<DUP>/<INV>) ou breakend
            elif (len(ref) == 1 and len(alt) == 1
                  and ref in _ACGT and alt in _ACGT):
                snps += 1
                if (ref, alt) in _TS:
                    ti += 1
                else:
                    tv += 1
            else:
                indels += 1
    if total == 0:
        extra = (" (%d alelo(s) nao-variante de gVCF ignorado(s))" % nonvar) if nonvar else ""
        return "[vcf] nenhuma variante encontrada%s." % extra
    titv = ("%.2f" % (ti / tv)) if tv else "n/a"
    out = ["VCF — %d variantes: %d SNPs, %d indels, %d SV/simbolicas"
           % (total, snps, indels, svs),
           "Ti=%d  Tv=%d  Ti/Tv=%s" % (ti, tv, titv)]
    if nonvar:
        out.append("(%d alelo(s) nao-variante de gVCF ignorado(s): <NON_REF>/<*>/*)"
                   % nonvar)
    out.append("por cromossomo (top 15):")
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
