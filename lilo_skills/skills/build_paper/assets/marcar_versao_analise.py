#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marcar_versao_analise.py — injeta ou remove a marcação de VERSÃO DE ANÁLISE
(banner vermelho + caixa de pendências) numa fonte Markdown PT, conforme
_REGRA_VERSAO_ANALISE_PT.md. Específico por formato (pandoc raw blocks):
LaTeX para PDF/TEX (xcolor + tcolorbox) e OpenXML para DOCX. Idempotente.

Uso:
  python marcar_versao_analise.py fonte_PT.md            # injeta (default)
  python marcar_versao_analise.py fonte_PT.md --strip    # remove a marcação
  python marcar_versao_analise.py fonte_PT.md -o saida.md # grava em outro arquivo

Sem -o, edita o arquivo no lugar. Requer no YAML:
  header-includes: [\\usepackage{xcolor}, \\usepackage{tcolorbox}]
(o template já traz; o injetor avisa se faltar.)
"""
import argparse, re, sys
from pathlib import Path

BEGIN = "<!-- BEGIN_ANALISE_MARCACAO -->"
END = "<!-- END_ANALISE_MARCACAO -->"

PENDENCIAS = [
    "Confirmar autoria, ordem dos coautores, afiliações e ORCIDs.",
    "Verificar conformidade ao escopo/instruções do periódico-alvo (formato, limite de palavras, figuras).",
    "Validar números-chave contra os dados-fonte versionados.",
    "Conferir referências cruzadas (figuras/tabelas/citações) após formatação final.",
    "Adicionar financiamento, conflitos de interesse, contribuições (CRediT) e disponibilidade de dados/código.",
    "Reconciliar versão PT <-> EN.",
    "Remover esta caixa e o banner vermelho antes do envio.",
]
BANNER_TXT = "[VERSÃO DE ANÁLISE E CORREÇÃO — PORTUGUÊS — NÃO SUBMETER]"


def bloco_latex():
    itens = "\n".join(rf"\item {p}" for p in PENDENCIAS)
    return (
        "```{=latex}\n"
        rf"\begin{{center}}\textcolor{{red}}{{\textbf{{\large {BANNER_TXT}}}}}\end{{center}}"
        "\n"
        r"\begin{tcolorbox}[colback=yellow!8,colframe=orange!70,"
        r"title=\textbf{Notas de análise e correção (pendências antes da submissão)}]"
        "\n\\small\n\\begin{itemize}\\setlength\\itemsep{1pt}\n"
        f"{itens}\n"
        "\\end{itemize}\n\\end{tcolorbox}\n"
        "```"
    )


def bloco_openxml():
    def p(texto, *, bold=False, color=None, center=False, sz=None):
        ppr = "<w:pPr>"
        if center:
            ppr += '<w:jc w:val="center"/>'
        ppr += "</w:pPr>" if ppr != "<w:pPr>" else ""
        if ppr == "<w:pPr>":
            ppr = ""
        rpr = "<w:rPr>"
        if bold:
            rpr += "<w:b/>"
        if color:
            rpr += f'<w:color w:val="{color}"/>'
        if sz:
            rpr += f'<w:sz w:val="{sz}"/>'
        rpr += "</w:rPr>"
        if rpr == "<w:rPr></w:rPr>":
            rpr = ""
        t = (texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{t}</w:t></w:r></w:p>'

    paras = [p(BANNER_TXT, bold=True, color="C00000", center=True, sz="26")]
    paras.append(p("Notas de análise e correção (pendências antes da submissão)",
                   bold=True, color="C55A11"))
    for it in PENDENCIAS:
        paras.append(p("•  " + it))
    return "```{=openxml}\n" + "\n".join(paras) + "\n```"


def marcacao():
    return f"{BEGIN}\n\n{bloco_latex()}\n\n{bloco_openxml()}\n\n{END}\n"


def split_frontmatter(txt):
    """Retorna (frontmatter_com_delimitadores, corpo). Suporta YAML --- ... ---."""
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", txt, flags=re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return "", txt


def strip_existing(corpo):
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?",
                  "", corpo, flags=re.DOTALL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fonte")
    ap.add_argument("-o", "--output")
    ap.add_argument("--strip", action="store_true",
                    help="remove a marcação (preparação para submissão)")
    a = ap.parse_args()

    src = Path(a.fonte)
    txt = src.read_text(encoding="utf-8")
    fm, corpo = split_frontmatter(txt)
    corpo = strip_existing(corpo).lstrip("\n")

    if not a.strip:
        if "tcolorbox" not in fm:
            print("AVISO: 'header-includes' sem tcolorbox/xcolor — o PDF pode "
                  "falhar. Adicione-os ao YAML (ver manuscrito_template.md).",
                  file=sys.stderr)
        corpo = marcacao() + "\n" + corpo
        acao = "injetada"
    else:
        acao = "removida"

    out = Path(a.output) if a.output else src
    out.write_text(fm + corpo, encoding="utf-8")
    print(f"Marcacao de analise {acao}: {out}")


if __name__ == "__main__":
    main()
