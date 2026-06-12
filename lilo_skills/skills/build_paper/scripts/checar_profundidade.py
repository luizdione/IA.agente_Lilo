#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar_profundidade.py — conta palavras por seção de uma fonte Markdown e
compara com as metas mínimas de profundidade (reference/estrutura_e_profundidade.md).
Metas são PISOS de conteúdo, não limites; abstract pode ter teto do periódico.

Uso: python checar_profundidade.py fonte.md [--abstract-max 250]
"""
import argparse, re, sys, unicodedata
from pathlib import Path

# metas mínimas por categoria de seção (palavras)
METAS = {"abstract": 350, "introducao": 600, "metodos": 700,
         "resultados": 900, "discussao": 700, "conclusao": 200}

# mapeia títulos (PT/EN) para categorias
PADROES = [
    ("abstract",   r"abstract|resumo"),
    ("introducao", r"introdu|introduction"),
    ("metodos",    r"m[ée]todos|materials?\s+and\s+methods|methods"),
    ("resultados", r"resultados|results"),
    ("discussao",  r"discuss[aã]o|discussion"),
    ("conclusao",  r"conclus[aã]o|conclusion"),
]


def cat(titulo):
    t = "".join(c for c in unicodedata.normalize("NFD", titulo.lower())
                if unicodedata.category(c) != "Mn")
    for nome, rx in PADROES:
        if re.search(rx, titulo.lower()) or re.search(rx, t):
            return nome
    return None


def conta_palavras(txt):
    txt = re.sub(r"```.*?```", " ", txt, flags=re.DOTALL)      # blocos de código/raw
    txt = re.sub(r"<!--.*?-->", " ", txt, flags=re.DOTALL)     # comentários
    txt = re.sub(r"[#>*_`|\-]+", " ", txt)                      # marcação
    return len(re.findall(r"\b[\wÀ-ÿ']+\b", txt))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fonte")
    ap.add_argument("--abstract-max", type=int, default=None,
                    help="teto de palavras do abstract do periódico-alvo")
    a = ap.parse_args()
    txt = Path(a.fonte).read_text(encoding="utf-8")

    # abstract do YAML (abstract: | ... ) entra como seção 'abstract'
    secoes = {}
    m = re.search(r"\nabstract:\s*\|(.*?)\n(?:[a-zA-Z_-]+:|---)", txt, flags=re.DOTALL)
    if m:
        secoes.setdefault("abstract", 0)
        secoes["abstract"] += conta_palavras(m.group(1))

    corpo = re.sub(r"^---\n.*?\n---\n", "", txt, flags=re.DOTALL)
    partes = re.split(r"^#{1,6}\s+(.*)$", corpo, flags=re.MULTILINE)
    # partes: [pre, titulo1, corpo1, titulo2, corpo2, ...]
    for i in range(1, len(partes) - 1, 2):
        c = cat(partes[i])
        if c:
            secoes[c] = secoes.get(c, 0) + conta_palavras(partes[i + 1])

    print(f"{'seção':<12}{'palavras':>10}{'meta':>8}   status")
    print("-" * 44)
    ok = True
    for nome in ["abstract", "introducao", "metodos", "resultados",
                 "discussao", "conclusao"]:
        n = secoes.get(nome)
        if n is None:
            print(f"{nome:<12}{'—':>10}{METAS[nome]:>8}   AUSENTE")
            ok = False
            continue
        meta = METAS[nome]
        status = "ok" if n >= meta else f"abaixo (+{meta-n})"
        if n < meta:
            ok = False
        linha = f"{nome:<12}{n:>10}{meta:>8}   {status}"
        if nome == "abstract" and a.abstract_max and n > a.abstract_max:
            linha += f"  [EXCEDE teto do periódico: {a.abstract_max}]"
            ok = False
        print(linha)
    print("-" * 44)
    print("Metas são pisos de conteúdo, não limites. Não preencha artificialmente.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
