#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_journal_profile.py — constrói/atualiza "perfis de estilo" por revista a
partir de FONTES LEGÍTIMAS:
  * OpenAlex (metadados + abstracts de qualquer revista, por ISSN)
  * Europe PMC (texto integral em JATS apenas de artigos OPEN-ACCESS)
  * PDFs locais a que VOCÊ tenha acesso legítimo (--local-pdfs)
NÃO baixa PDFs pagos sob paywall.

Cada perfil (journals/profiles/<slug>.json) contém:
  - section_norms: tamanho por seção em palavras/caracteres (mediana, p25, p75)
    -> NORMAS EMPÍRICAS observadas, NÃO regras da revista.
  - abstract_stats: idem para o resumo.
  - citation: estilo no texto (numeric vs author-year) e ordenação da lista.
  - references_stats: nº de referências por artigo.
  - semantics: comprimento médio de frase, conectivos e frases de abertura comuns.
  - provenance: fontes, datas, n amostrado, quantos com texto integral.

Uso:
  python build_journal_profile.py --list
  python build_journal_profile.py --name "Acta Tropica" --n 10 --mailto voce@ex.com
  python build_journal_profile.py --issn 0268-9146 --n 10
  python build_journal_profile.py --all --n 10
  python build_journal_profile.py --update                 # re-roda perfis já existentes
  python build_journal_profile.py --name "..." --local-pdfs "C:/pasta/pdfs"
"""
import argparse, json, re, sys, time, unicodedata
from collections import Counter
from pathlib import Path
from statistics import median

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Instale:  pip install -r ml/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent          # .../build_paper
REG = ROOT / "journals" / "registry.json"
PROFILES = ROOT / "journals" / "profiles"
OPENALEX = "https://api.openalex.org/works"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = {"User-Agent": "build_paper-profiler/1.0 (mailto:%s)"}

SECOES = {
    "introduction": r"^\s*(?:\d+\.?\s*)?(introduction|background|introdu)",
    "methods": r"^\s*(?:\d+\.?\s*)?(materials?\s+and\s+methods|methods|methodology|m[ée]todos|material e m)",
    "results": r"^\s*(?:\d+\.?\s*)?(results|resultados)",
    "discussion": r"^\s*(?:\d+\.?\s*)?(discussion|discuss[aã]o)",
    "conclusion": r"^\s*(?:\d+\.?\s*)?(conclusions?|concluding|conclus[aã]o)",
}


# ----------------------------- utilidades -----------------------------
def slug(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def words(t):
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", t or ""))


def pctls(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    def q(p):
        if len(xs) == 1:
            return xs[0]
        i = p * (len(xs) - 1)
        lo = int(i); frac = i - lo
        return round(xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * frac, 1)
    return {"n": len(xs), "min": xs[0], "p25": q(0.25), "median": round(median(xs), 1),
            "p75": q(0.75), "max": xs[-1]}


def load_registry():
    return json.loads(REG.read_text(encoding="utf-8"))


def find_journal(reg, *, issn=None, name=None):
    for j in reg["journals"]:
        if issn and issn in j["issn"]:
            return j
        if name and slug(name) == slug(j["name"]):
            return j
    return None


# ----------------------------- coleta ---------------------------------
def reconstruct_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def openalex_recent(issn, n, mailto):
    hdr = {"User-Agent": UA["User-Agent"] % (mailto or "anon@example.com")}
    params = {
        "filter": f"primary_location.source.issn:{issn},type:article",
        "sort": "publication_date:desc",
        "per-page": min(max(n, 1), 50),
        "mailto": mailto or "anon@example.com",
    }
    r = requests.get(OPENALEX, params=params, headers=hdr, timeout=40)
    r.raise_for_status()
    out = []
    for w in r.json().get("results", [])[:n]:
        out.append({
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
            "n_refs": w.get("referenced_works_count"),
            "is_oa": (w.get("open_access") or {}).get("is_oa"),
            "pmcid": (w.get("ids") or {}).get("pmcid"),
        })
    return out


def epmc_fulltext(doi):
    """Retorna JATS XML (str) de artigo OA via Europe PMC, ou None."""
    try:
        s = requests.get(f"{EPMC}/search",
                         params={"query": f'DOI:"{doi}"', "resultType": "core",
                                 "format": "json"}, timeout=40)
        res = s.json().get("resultList", {}).get("result", [])
        if not res:
            return None
        rec = res[0]
        if str(rec.get("isOpenAccess", "N")).upper() not in ("Y", "TRUE"):
            return None
        src, pid = rec.get("source"), rec.get("id")
        if not (src and pid):
            return None
        f = requests.get(f"{EPMC}/{src}/{pid}/fullTextXML", timeout=60)
        return f.text if f.ok and "<" in f.text else None
    except Exception:
        return None


def parse_jats(xml):
    """Segmenta JATS em seções IMRaD + referências (usa lxml se houver)."""
    try:
        from lxml import etree
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return None
    def txt(el):
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip()
    secs = {}
    for sec in root.iter("{*}sec"):
        title_el = sec.find("{*}title")
        title = (txt(title_el) if title_el is not None else "").lower()
        for key, rx in SECOES.items():
            if re.search(rx, title, re.I) and key not in secs:
                secs[key] = txt(sec)
    abs = root.find(".//{*}abstract")
    if abs is not None:
        secs["abstract"] = txt(abs)
    refs = [txt(r) for r in root.iter("{*}ref")]
    secs["_refs"] = refs
    return secs


def pdf_sections(path):
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        return None
    return segment_plaintext(text)


def segment_plaintext(text):
    lines = text.splitlines()
    idx = []
    for i, ln in enumerate(lines):
        for key, rx in {**SECOES, "abstract": r"^\s*abstract\b|^\s*resumo\b",
                        "references": r"^\s*references\b|^\s*refer[êe]ncias\b"}.items():
            if re.search(rx, ln.strip(), re.I) and len(ln.strip()) < 60:
                idx.append((i, key))
                break
    secs = {}
    for j, (i, key) in enumerate(idx):
        end = idx[j + 1][0] if j + 1 < len(idx) else len(lines)
        if key not in secs:
            secs[key] = "\n".join(lines[i + 1:end]).strip()
    return secs or None


# ----------------------------- análise --------------------------------
def detect_citation(corpus_text, ref_samples):
    num = len(re.findall(r"\[\d+(?:[-,–]\s?\d+)*\]", corpus_text))
    ay = len(re.findall(r"\([A-Z][A-Za-zÀ-ÿ'-]+(?:\s+et\s+al\.?)?,?\s+\d{4}[a-z]?\)", corpus_text))
    in_text = "numeric" if num > ay * 1.5 else "author-year" if ay > num * 1.5 else "unknown"
    ordering = "unknown"
    firsts = [r.strip()[:40] for r in (ref_samples or []) if r.strip()][:12]
    if firsts:
        if sum(bool(re.match(r"^\[?\d+[\].]", f)) for f in firsts) >= len(firsts) * 0.6:
            ordering = "by-number"
        else:
            caps = [re.match(r"^([A-Z][A-Za-zÀ-ÿ'-]+)", f) for f in firsts]
            names = [c.group(1).lower() for c in caps if c]
            if names and names == sorted(names):
                ordering = "alphabetical"
    return {"in_text": in_text, "ordering": ordering,
            "_counts": {"numeric": num, "author_year": ay}}


CONECTIVOS = ["however", "moreover", "furthermore", "therefore", "in addition",
              "notably", "importantly", "consistent with", "in contrast",
              "taken together", "of note", "interestingly", "remarkably"]


def semantics(text):
    sents = re.split(r"(?<=[.!?])\s+", text)
    sents = [s for s in sents if len(s) > 20]
    avg_len = round(sum(words(s) for s in sents) / len(sents), 1) if sents else None
    low = text.lower()
    conn = {c: low.count(c) for c in CONECTIVOS if low.count(c)}
    openers = Counter()
    for s in sents:
        first3 = " ".join(s.split()[:3]).strip().lower()
        if first3:
            openers[first3] += 1
    return {"avg_sentence_words": avg_len,
            "connectives": dict(sorted(conn.items(), key=lambda x: -x[1])[:10]),
            "common_openers": dict(openers.most_common(8))}


# ----------------------------- perfil ---------------------------------
def build_profile(journal, n, mailto, local_pdfs):
    name, issns = journal["name"], journal["issn"]
    print(f"\n=== {name} (ISSN {', '.join(issns)}) ===")
    works = []
    for issn in issns:
        try:
            works = openalex_recent(issn, n, mailto)
            if works:
                print(f"  OpenAlex: {len(works)} artigos recentes (ISSN {issn}).")
                break
        except Exception as e:
            print(f"  OpenAlex falhou p/ {issn}: {e}")
    sec_words = {k: [] for k in list(SECOES) + ["abstract"]}
    sec_chars = {k: [] for k in list(SECOES) + ["abstract"]}
    n_refs, ft_count = [], 0
    corpus, ref_samples = [], []

    for w in works:
        if w["abstract"]:
            sec_words["abstract"].append(words(w["abstract"]))
            sec_chars["abstract"].append(len(w["abstract"]))
            corpus.append(w["abstract"])
        if w["n_refs"]:
            n_refs.append(w["n_refs"])
        secs = epmc_fulltext(w["doi"]) and parse_jats(epmc_fulltext(w["doi"])) if w["is_oa"] and w["doi"] else None
        if secs:
            ft_count += 1
            for k in SECOES:
                if secs.get(k):
                    sec_words[k].append(words(secs[k]))
                    sec_chars[k].append(len(secs[k]))
                    corpus.append(secs[k])
            ref_samples += secs.get("_refs", [])
        time.sleep(0.34)   # cortesia com as APIs

    # PDFs locais (acesso legítimo seu)
    if local_pdfs:
        for pdf in Path(local_pdfs).glob("*.pdf"):
            secs = pdf_sections(pdf)
            if not secs:
                continue
            ft_count += 1
            for k in list(SECOES) + ["abstract"]:
                if secs.get(k):
                    sec_words[k].append(words(secs[k]))
                    sec_chars[k].append(len(secs[k]))
                    corpus.append(secs[k])
            print(f"  PDF local incorporado: {pdf.name}")

    corpus_text = "\n".join(corpus)
    profile = {
        "journal": name, "issn": issns, "area": journal.get("area"),
        "oa": journal.get("oa"),
        "provenance": {
            "built": time.strftime("%Y-%m-%d %H:%M"),
            "sources": ["OpenAlex", "Europe PMC (OA)"] + (["local PDFs"] if local_pdfs else []),
            "n_sampled": len(works), "n_fulltext": ft_count,
            "note": "section_norms são NORMAS EMPÍRICAS observadas, não regras da revista. Confirme limites no Guide for Authors.",
        },
        "abstract_stats": {"words": pctls(sec_words["abstract"]), "chars": pctls(sec_chars["abstract"])},
        "section_norms": {k: {"words": pctls(sec_words[k]), "chars": pctls(sec_chars[k])}
                          for k in SECOES if sec_words[k]},
        "references_stats": {"count_per_article": pctls(n_refs)},
        "citation": detect_citation(corpus_text, ref_samples) if corpus_text else {"in_text": "unknown"},
        "semantics": semantics(corpus_text) if corpus_text else {},
    }
    # preserva citation_style curado do registry se o corpus não decidiu
    if profile["citation"].get("in_text") == "unknown" and journal.get("citation_style"):
        profile["citation"]["in_text"] = journal["citation_style"]
        profile["citation"]["_source"] = "registry (curado)"

    PROFILES.mkdir(parents=True, exist_ok=True)
    out = PROFILES / f"{slug(name)}.json"
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> perfil salvo: {out}  (full-text: {ft_count}/{len(works)})")
    return out


# ----------------------------- CLI ------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--issn")
    ap.add_argument("--name")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--update", action="store_true", help="re-roda perfis já existentes")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--mailto", default=None, help="e-mail p/ 'polite pool' das APIs")
    ap.add_argument("--local-pdfs", default=None)
    a = ap.parse_args()
    reg = load_registry()

    if a.list:
        for j in reg["journals"]:
            mark = "OA" if j.get("oa") == "oa" else j.get("oa", "")
            print(f'  [{mark:>6}] {j["name"]}  (ISSN {", ".join(j["issn"])})')
        return

    targets = []
    if a.all:
        targets = reg["journals"]
    elif a.update:
        done = {p.stem for p in PROFILES.glob("*.json")}
        targets = [j for j in reg["journals"] if slug(j["name"]) in done]
        if not targets:
            print("Nenhum perfil prévio para atualizar.")
            return
    else:
        j = find_journal(reg, issn=a.issn, name=a.name)
        if not j:
            sys.exit("Revista não encontrada no registry. Use --list, --issn ou --name.")
        targets = [j]

    for j in targets:
        try:
            build_profile(j, a.n, a.mailto, a.local_pdfs)
        except Exception as e:
            print(f"  ERRO em {j['name']}: {e}")


if __name__ == "__main__":
    main()
