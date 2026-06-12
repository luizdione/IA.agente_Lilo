#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar_signposting.py — gate de coesão narrativa (reference/estrutura_e_profundidade.md).

Sinaliza "parágrafos-ilha": subseções de Resultados e parágrafos/viradas da Discussão
cuja ÚLTIMA frase NÃO é uma frase-ponte (não levanta a pergunta/tensão que a próxima
unidade resolve). É um auxílio HEURÍSTICO — flag = "revisar", não "erro": confirme no texto.

Classificação por unidade:
  OK      última frase é pergunta (?) ou tem pista de signposting para frente.
  OK*     última frase é plana, MAS o abridor da próxima unidade já carrega a transição
          (ponte adiantada) — aceitável, embora o ideal seja o peso no fim da unidade.
  REVISAR última frase plana e a próxima também não retoma — provável parágrafo-ilha.

Cobre Resultados (cada subseção ##/###) e Discussão (cada parágrafo). A última unidade
de cada seção é isenta (conduz à seção seguinte). Aplica-se a EN e PT.

Uso:
  python checar_signposting.py PAPER/src/manuscrito_EN.md [mais.md ...]
  python checar_signposting.py *.md --section discussion --warn-only
Saída: relatório por arquivo; exit 1 se houver REVISAR (use --warn-only p/ exit 0).
"""
import argparse, re, sys
from pathlib import Path

# console do Windows (cp1252) não imprime ↳/—/ç; força UTF-8 na saída
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- pistas de "frase-ponte" (olham para FRENTE) -------------------------------
# frases (substring, minúsculas) — EN + PT
PONTE_FRASES = [
    # EN
    "raises the question", "raises a different question", "the question becomes",
    "the question of", "turns the question", "turns to", "we next", "we then",
    "we therefore", "we asked", "we examined", "we sought", "next asked",
    "first thing", "asks for", "only worth", "to answer", "can be tested",
    "tested independently", "remains to", "remained to", "natural next",
    "next step", "set against", "depends on", "points to", "in particular",
    "above all", "rests on", "rests, above all", "now to be", "set the stage",
    "sets the stage", "would have to", "is only", "is what", "what justifies",
    # PT
    "a seguir", "perguntamos", "passamos a", "passo natural", "próximo passo",
    "passo seguinte", "só vale", "só se", "resta dissecar", "a aguardar",
    "fora construído", "o que significa", "o que justifica", "é o que justifica",
    "antes de", "deve corresponder", "à espera de", "por demonstrar",
    "resta ", "sobretudo", "em particular", "repousa sobre", "repousa, sobretudo",
]
# palavras isoladas (\bword\b) — pistas mais curtas/ambíguas
PONTE_PALAVRAS = [
    # EN
    "whether", "question", "demanded", "prediction", "falsifiable", "awaiting",
    "hypotheses", "if", "should", "could", "would", "next", "then", "first",
    "remains", "agenda",
    # PT
    "questão", "exigia", "exigiu", "exige", "demanda", "levanta", "justifica",
    "deveria", "aguarda", "faltava", "hipóteses", "agenda", "se",
]

# --- pistas de "abridor que retoma" (na 1a frase da PRÓXIMA unidade) -----------
ABRIDOR_FRASES = [
    # EN
    "to ask whether", "to answer this", "having confirmed", "having established",
    "the same", "the phenotypes above", "beyond the", "integrating these",
    "this computational", "several limitations", "testable hypotheses",
    "we now", "to follow", "to test", "both arms", "both genetic",
    # PT
    "para perguntar", "para responder", "tendo confirmado", "tendo estabelecido",
    "o mesmo", "os fenótipos anteriores", "para além", "a integração",
    "essa conexão", "algumas limitações", "hipóteses testáveis", "passamos agora",
    "para acompanhar", "ambos os braços", "testamos essa",
]

ABREV = (r"et al|e\.g|i\.e|cf|vs|ca|approx|aprox|fig|figs|figura|figuras|no|"
         r"dr|prof|eq|ref|al|sp|str|ca|cap|seç|sec|p\.ex|ex")


def limpa_md(s):
    s = re.sub(r"`[^`]*`", " ", s)                 # código inline
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)     # imagens
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # links -> texto
    s = re.sub(r"[*_~]+", "", s)                     # ênfase
    s = re.sub(r"\s+", " ", s).strip()
    return s


def frases(par):
    """Divide um parágrafo (prosa) em frases, protegendo abreviações e decimais."""
    t = limpa_md(par)
    t = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", t)                  # decimais 0.37
    t = re.sub(rf"\b({ABREV})\.", r"\1<DOT>", t, flags=re.I)    # abreviações
    partes = re.split(r"(?<=[.?!;])\s+", t)                     # ; também encerra ideia
    out = []
    for p in partes:
        p = p.replace("<DOT>", ".").strip()
        if p:
            out.append(p)
    return out


def tem_ponte(frase):
    f = frase.lower()
    if f.rstrip().endswith("?"):
        return True
    for fr in PONTE_FRASES:
        if fr in f:
            return True
    for w in PONTE_PALAVRAS:
        if re.search(rf"\b{re.escape(w)}\b", f):
            return True
    return False


def tem_abridor(frase):
    f = frase.lower()
    if f.rstrip().endswith("?"):
        return True
    return any(a in f for a in ABRIDOR_FRASES)


def eh_prosa(bloco):
    b = bloco.lstrip()
    if b.startswith("![") or b.startswith("|"):
        return False
    if re.match(r"\*\*(table|tabela|figure|figura)\b", b, flags=re.I):
        return False
    linhas = [l for l in bloco.splitlines() if l.strip()]
    if linhas and all(l.lstrip().startswith("|") for l in linhas):
        return False
    return True


def blocos(texto):
    return [b.strip() for b in re.split(r"\n\s*\n", texto) if b.strip()]


def prosa_final(texto):
    """Último bloco de PROSA (ignora figuras/tabelas/legendas)."""
    pr = [b for b in blocos(texto) if eh_prosa(b)]
    return pr[-1] if pr else None


def primeira_prosa(texto):
    pr = [b for b in blocos(texto) if eh_prosa(b)]
    return pr[0] if pr else None


def coleta_unidades(txt):
    """Retorna (unidades_resultados, unidades_discussao). Cada unidade = (rótulo, corpo)."""
    corpo = re.sub(r"^---\n.*?\n---\n", "", txt, flags=re.DOTALL)
    linhas = corpo.splitlines()
    top = None
    res, disc = [], []           # res: [(label, body_text)]; disc: corpo cru
    sub_label, sub_buf = None, []
    disc_buf = []

    def flush_sub():
        nonlocal sub_label, sub_buf
        if sub_label is not None and "\n".join(sub_buf).strip():
            res.append((sub_label, "\n".join(sub_buf)))
        sub_label, sub_buf = None, []

    for ln in linhas:
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            nivel, titulo = len(m.group(1)), m.group(2).strip()
            tl = titulo.lower()
            if nivel == 1:
                flush_sub()
                if disc_buf:
                    disc.append("\n".join(disc_buf)); disc_buf = []
                if re.search(r"result|resultado", tl):
                    top = "res"; sub_label = titulo  # intro antes do 1o ## vai aqui
                elif re.search(r"discuss", tl):
                    top = "disc"
                else:
                    top = "outro"
                continue
            if top == "res" and nivel in (2, 3):
                flush_sub()
                sub_label = titulo
                continue
        # linha de conteúdo
        if top == "res":
            if sub_label is not None:
                sub_buf.append(ln)
        elif top == "disc":
            disc_buf.append(ln)
    flush_sub()
    if disc_buf:
        disc.append("\n".join(disc_buf))

    # discussão: 1 unidade por parágrafo de prosa
    disc_pars = []
    disc_txt = "\n\n".join(disc)
    for i, b in enumerate([b for b in blocos(disc_txt) if eh_prosa(b)], 1):
        disc_pars.append((f"¶{i}", b))
    return res, disc_pars


def avalia(unidades):
    """Marca cada unidade. Retorna lista de dicts. Última unidade = terminal (isenta)."""
    out = []
    n = len(unidades)
    for i, (label, body) in enumerate(unidades):
        fp = prosa_final(body)
        if not fp:
            continue  # unidade sem prosa (ex.: ## só com ### filhos)
        ult = frases(fp)
        if not ult:
            continue
        ultima = ult[-1]
        terminal = (i == n - 1)
        if terminal:
            status = "terminal"
        elif tem_ponte(ultima):
            status = "OK"
        else:
            # ponte adiantada no abridor da próxima unidade?
            prox = unidades[i + 1][1] if i + 1 < n else ""
            pp = primeira_prosa(prox)
            ab = frases(pp)[0] if pp and frases(pp) else ""
            status = "OK*" if ab and tem_abridor(ab) else "REVISAR"
        out.append(dict(label=label, status=status, frase=ultima))
    return out


def imprime(titulo, avaliacoes, mostra_ok):
    print(f"\n## {titulo}")
    if not avaliacoes:
        print("  (sem unidades de prosa detectadas)")
        return 0
    revisar = 0
    for a in avaliacoes:
        if a["status"] in ("OK", "terminal") and not mostra_ok:
            continue
        tag = {"OK": "ok   ", "OK*": "ok*  ", "REVISAR": "REVISAR", "terminal": "term "}[a["status"]]
        if a["status"] == "REVISAR":
            revisar += 1
        fr = a["frase"]
        fr = (fr[:150] + "…") if len(fr) > 151 else fr
        print(f"  [{tag}] {a['label']}")
        if a["status"] in ("REVISAR", "OK*") or mostra_ok:
            print(f"           -> \"{fr}\"")
    return revisar


def main():
    ap = argparse.ArgumentParser(description="Gate de signposting (parágrafos-ilha).")
    ap.add_argument("fontes", nargs="+", help="um ou mais .md de manuscrito")
    ap.add_argument("--section", choices=["results", "discussion", "both"],
                    default="both")
    ap.add_argument("--show-ok", action="store_true",
                    help="lista também as unidades OK/terminais")
    ap.add_argument("--warn-only", action="store_true",
                    help="não retorna erro (exit 0) mesmo havendo REVISAR")
    a = ap.parse_args()

    total_revisar = 0
    for f in a.fontes:
        p = Path(f)
        if not p.exists():
            print(f"!! não encontrado: {f}"); total_revisar += 1; continue
        txt = p.read_text(encoding="utf-8")
        res, disc = coleta_unidades(txt)
        print(f"\n=== {p.name} ===")
        if a.section in ("results", "both"):
            total_revisar += imprime("Resultados (subseções)", avalia(res), a.show_ok)
        if a.section in ("discussion", "both"):
            total_revisar += imprime("Discussão (parágrafos)", avalia(disc), a.show_ok)

    print("\n" + "-" * 60)
    if total_revisar:
        print(f"{total_revisar} unidade(s) marcada(s) REVISAR — confirme se a última "
              f"frase levanta a pergunta da próxima. Heurístico: pode haver falso-positivo.")
    else:
        print("Nenhum parágrafo-ilha provável. (Heurístico — não dispensa leitura.)")
    print("Regra: reference/estrutura_e_profundidade.md → Signposting.")
    sys.exit(0 if (total_revisar == 0 or a.warn_only) else 1)


if __name__ == "__main__":
    main()
