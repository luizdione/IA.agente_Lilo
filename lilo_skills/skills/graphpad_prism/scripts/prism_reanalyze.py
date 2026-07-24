#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prism_reanalyze.py — Re-análise e auditoria estatística de tabelas extraídas do Prism.

Recebe um CSV (ou uma pasta de extração com tabelas/*.csv), reconstrói os grupos e
RECALCULA a estatística de forma independente, para comparar com o que o Prism
reportou (reprodutibilidade / integridade dos dados). Não substitui o Prism — serve
para auditar: bate a média? o n? o teste é apropriado? as premissas se sustentam?

Para cada grupo: n, média, DP, EPM (SEM), mediana, IC95%.
Comparação entre grupos:
  - 2 grupos  -> t de Student e t de Welch, Mann-Whitney U, d de Cohen, Levene, Shapiro.
  - >2 grupos -> ANOVA de uma via (F, p), Kruskal-Wallis, eta², Levene, Shapiro por grupo,
                 e t pareado-a-pareado com correção de Holm.
Checagens de premissa (normalidade Shapiro; homocedasticidade Levene) são reportadas
porque são exatamente o que um revisor questiona.

AVISO: ANOVA de uma via aqui trata colunas como grupos INDEPENDENTES. Se o desenho
original era de medidas repetidas (RM) ou two-way (como muitos projetos do Prism),
os p-valores diferem — isto é uma triagem, não a reprodução do modelo exato. Para
reproduzir RM/two-way fielmente, use os dados brutos em .pzfx e um modelo dedicado
(R: afex/ez; Python: pingouin/statsmodels).

Uso:
  python prism_reanalyze.py CSV_OU_PASTA [--long] [--wide] [--out relatorio.md] [--quiet]

Requer: numpy, scipy, pandas.
"""
from __future__ import annotations
import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# colunas que são índice/rótulo/eixo-X, NUNCA um grupo de dados (mesmo que numéricas)
LABEL_COLS = {"linha", "row", "rotulo_ou_contexto", "x"}


# --------------------------------------------------------------- leitura/limpeza

def _to_num(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    # ponto excluído no Prism (marcado "[EXCLUÍDO]" pelo extrator) -> NaN, NUNCA
    # o valor bruto; caso contrário o recálculo usaria dado que o Prism descartou.
    mask_excl = s.str.contains("EXCLU", case=False, na=False)
    num = pd.to_numeric(s.str.replace(",", ".", regex=False).str.strip(), errors="coerce")
    return num.mask(mask_excl)


def load_groups(csv: Path, force_long=False, force_wide=False) -> dict[str, np.ndarray]:
    """Retorna {nome_grupo: array de valores}. Detecta formato long (rotulo,valor)
    ou wide (cada coluna numérica = um grupo)."""
    df = pd.read_csv(csv, encoding="utf-8-sig")
    df = df.dropna(axis=1, how="all")
    if df.shape[1] == 0:
        return {}

    cols = list(df.columns)
    # formato long: 2 colunas, a 2ª predominantemente numérica e a 1ª não
    looks_long = (df.shape[1] == 2 and
                  _to_num(df[cols[1]]).notna().mean() > 0.6 and
                  _to_num(df[cols[0]]).notna().mean() < 0.6)
    # --long só é aplicável com >=2 colunas; senão cai para o ramo wide (que trata
    # 1 coluna graciosamente), evitando IndexError em cols[1].
    if (force_long and df.shape[1] >= 2) or (looks_long and not force_wide):
        lab, val = cols[0], cols[1]
        g = {}
        vv = _to_num(df[val])
        for key, idx in df.groupby(df[lab].astype(str)).groups.items():
            arr = vv.loc[idx].dropna().to_numpy()
            if arr.size:
                g[str(key)] = arr
        return g

    # formato wide: cada coluna numérica é um grupo.
    # Colunas de índice/rótulo/X (LABEL_COLS) são descartadas SEMPRE — inclusive
    # quando numéricas (ex.: "Linha" = tempos 0/15/30/60), desde que reste dado.
    data_cols = [c for c in cols if str(c).lower() not in LABEL_COLS]
    pooled = OrderedDict()  # base -> [arrays]  (agrega réplicas _repN do mesmo grupo)
    for c in cols:
        if str(c).lower() in LABEL_COLS and len(data_cols) >= 1:
            continue
        arr = _to_num(df[c]).dropna().to_numpy()
        if arr.size < 1:
            continue
        base = re.sub(r"_rep\d+$", "", str(c))  # Grupo_rep1/2/3 -> Grupo
        pooled.setdefault(base, []).append(arr)
    return {base: np.concatenate(arrs) for base, arrs in pooled.items()}


# --------------------------------------------------------------- estatística

def describe(arr: np.ndarray) -> dict:
    n = arr.size
    m = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if n > 1 else float("nan")
    sem = sd / np.sqrt(n) if n > 1 else float("nan")
    if n > 1:
        tcrit = stats.t.ppf(0.975, n - 1)
        ci = (m - tcrit * sem, m + tcrit * sem)
    else:
        ci = (float("nan"), float("nan"))
    return {"n": n, "media": m, "DP": sd, "EPM": sem, "mediana": float(np.median(arr)),
            "IC95_low": ci[0], "IC95_high": ci[1]}


def cohens_d(a, b):
    na, nb = a.size, b.size
    if na < 2 or nb < 2:
        return float("nan")
    sp = np.sqrt(((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2))
    return float((np.mean(a) - np.mean(b)) / sp) if sp > 0 else float("nan")


def holm_correction(pvals):
    """Correção de Holm-Bonferroni. Retorna p-ajustados na ordem original."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    prev = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        prev = max(prev, min(val, 1.0))
        adj[idx] = prev
    return adj


def analyze(groups: dict[str, np.ndarray]) -> dict:
    out = {"grupos": {}, "comparacao": {}, "premissas": {}, "avisos": []}
    for name, arr in groups.items():
        out["grupos"][name] = describe(arr)

    names = list(groups.keys())
    arrs = [groups[n] for n in names]
    usable = [a for a in arrs if a.size >= 3]

    # premissas
    for name, arr in groups.items():
        if arr.size >= 3:
            try:
                W, p = stats.shapiro(arr)
                out["premissas"][name] = {"shapiro_W": float(W), "shapiro_p": float(p),
                                          "normal_5pct": bool(p > 0.05)}
            except Exception:
                pass
    if len(usable) >= 2:
        try:
            Lstat, Lp = stats.levene(*usable, center="median")
            out["premissas"]["_levene"] = {"stat": float(Lstat), "p": float(Lp),
                                           "homocedastico_5pct": bool(Lp > 0.05)}
        except Exception:
            pass

    # comparações
    if len(names) == 2 and all(a.size >= 2 for a in arrs):
        a, b = arrs
        ts, ps = stats.ttest_ind(a, b, equal_var=True)
        tw, pw = stats.ttest_ind(a, b, equal_var=False)
        try:
            u, pu = stats.mannwhitneyu(a, b, alternative="two-sided")
        except ValueError:
            u, pu = float("nan"), float("nan")
        out["comparacao"] = {
            "tipo": "2 grupos",
            "t_student": {"t": float(ts), "p": float(ps)},
            "t_welch": {"t": float(tw), "p": float(pw)},
            "mann_whitney": {"U": float(u), "p": float(pu)},
            "cohen_d": cohens_d(a, b),
        }
    elif len(names) > 2 and len(usable) >= 2:
        F, pF = stats.f_oneway(*[a for a in arrs if a.size >= 2])
        try:
            H, pH = stats.kruskal(*[a for a in arrs if a.size >= 2])
        except ValueError:
            H, pH = float("nan"), float("nan")
        # eta² = SSbetween / SStotal — calculado sobre EXATAMENTE os mesmos grupos
        # usados na ANOVA/Kruskal (size>=2), senão um singleton distorce o eta²
        # e ele deixa de corresponder ao F reportado.
        used = [a for a in arrs if a.size >= 2]
        allv = np.concatenate(used)
        grand = allv.mean()
        ssb = sum(a.size * (a.mean() - grand) ** 2 for a in used)
        sst = float(np.sum((allv - grand) ** 2))
        eta2 = float(ssb / sst) if sst > 0 else float("nan")
        # pairwise Holm
        pairs, praw = [], []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if arrs[i].size >= 2 and arrs[j].size >= 2:
                    _, p = stats.ttest_ind(arrs[i], arrs[j], equal_var=False)
                    pairs.append((names[i], names[j])); praw.append(p)
        padj = holm_correction(praw) if praw else []
        pairwise = [{"grupos": f"{g1} vs {g2}", "p_bruto": float(pr), "p_holm": float(pa),
                     "signif_5pct": bool(pa < 0.05)}
                    for (g1, g2), pr, pa in zip(pairs, praw, padj)]
        out["comparacao"] = {
            "tipo": f"{len(names)} grupos",
            "anova_oneway": {"F": float(F), "p": float(pF)},
            "kruskal_wallis": {"H": float(H), "p": float(pH)},
            "eta2": eta2,
            "pairwise_holm": pairwise,
        }
        out["avisos"].append(
            "ANOVA de uma via com grupos independentes. Se o desenho era RM/two-way, "
            "reproduza com modelo dedicado (R: afex; Python: pingouin).")
    else:
        out["avisos"].append("Grupos insuficientes ou n muito pequeno para teste inferencial.")
    return out


# --------------------------------------------------------------- relatório

def fmt_p(p):
    if p != p:  # nan
        return "—"
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def report_md(csv: Path, res: dict) -> str:
    L = [f"# Re-análise / auditoria estatística — `{csv.name}`", ""]
    L.append("## Estatística descritiva por grupo")
    L.append("| Grupo | n | Média | DP | EPM | Mediana | IC95% |")
    L.append("|---|--:|--:|--:|--:|--:|:--|")
    for name, d in res["grupos"].items():
        ci = f"[{d['IC95_low']:.3g}, {d['IC95_high']:.3g}]" if d["n"] > 1 else "—"
        L.append(f"| {name} | {d['n']} | {d['media']:.4g} | {d['DP']:.4g} | "
                 f"{d['EPM']:.4g} | {d['mediana']:.4g} | {ci} |")
    L.append("")

    if res.get("premissas"):
        L.append("## Premissas")
        for k, v in res["premissas"].items():
            if k == "_levene":
                L.append(f"- **Levene (homocedasticidade):** stat={v['stat']:.3g}, "
                         f"p={fmt_p(v['p'])} → {'OK' if v['homocedastico_5pct'] else 'VIOLADA'}")
            else:
                L.append(f"- **Shapiro {k}:** W={v['shapiro_W']:.3g}, p={fmt_p(v['shapiro_p'])} "
                         f"→ {'normal' if v['normal_5pct'] else 'NÃO normal'}")
        L.append("")

    c = res.get("comparacao", {})
    if c:
        L.append(f"## Comparação ({c.get('tipo','')})")
        if "t_student" in c:
            L.append(f"- **t de Student:** t={c['t_student']['t']:.3g}, p={fmt_p(c['t_student']['p'])}")
            L.append(f"- **t de Welch:** t={c['t_welch']['t']:.3g}, p={fmt_p(c['t_welch']['p'])}")
            L.append(f"- **Mann-Whitney U:** U={c['mann_whitney']['U']:.3g}, p={fmt_p(c['mann_whitney']['p'])}")
            L.append(f"- **d de Cohen:** {c['cohen_d']:.3g}")
        elif "anova_oneway" in c:
            L.append(f"- **ANOVA 1-via:** F={c['anova_oneway']['F']:.3g}, p={fmt_p(c['anova_oneway']['p'])}")
            L.append(f"- **Kruskal-Wallis:** H={c['kruskal_wallis']['H']:.3g}, p={fmt_p(c['kruskal_wallis']['p'])}")
            L.append(f"- **η² (eta²):** {c['eta2']:.3g}")
            if c.get("pairwise_holm"):
                L.append("\n| Par | p bruto | p (Holm) | signif. |")
                L.append("|---|--:|--:|:--:|")
                for pw in c["pairwise_holm"]:
                    L.append(f"| {pw['grupos']} | {fmt_p(pw['p_bruto'])} | {fmt_p(pw['p_holm'])} | "
                             f"{'sim' if pw['signif_5pct'] else 'não'} |")
        L.append("")
    if res.get("avisos"):
        L.append("## Avisos")
        for w in res["avisos"]:
            L.append(f"- {w}")
        L.append("")
    return "\n".join(L)


# --------------------------------------------------------------- main

def run_one(csv: Path, force_long, force_wide, quiet) -> str | None:
    groups = load_groups(csv, force_long, force_wide)
    if len(groups) < 1:
        if not quiet:
            print(f"[reanalyze] sem grupos numéricos utilizáveis em {csv.name}", file=sys.stderr)
        return None
    res = analyze(groups)
    return report_md(csv, res)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Re-análise/auditoria estatística de tabelas do Prism.")
    ap.add_argument("caminho", help="CSV ou pasta de extração (usa tabelas/*.csv)")
    ap.add_argument("--long", action="store_true", help="forçar formato long (rotulo,valor)")
    ap.add_argument("--wide", action="store_true", help="forçar formato wide (colunas=grupos)")
    ap.add_argument("--out", default=None, help="arquivo .md de saída (default: reanalise.md ao lado)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    path = Path(a.caminho)
    if path.is_dir():
        csvs = sorted((path / "tabelas").glob("*.csv")) or sorted(path.glob("*.csv"))
    else:
        csvs = [path]
    if not csvs:
        print("Nenhum CSV encontrado.", file=sys.stderr)
        return 1

    blocks = []
    for c in csvs:
        md = run_one(c, a.long, a.wide, a.quiet)
        if md:
            blocks.append(md)
            if not a.quiet:
                print(f"[reanalyze] OK: {c.name}", file=sys.stderr)
    if not blocks:
        print("Nada re-analisado (tabelas sem estrutura de grupos numéricos).", file=sys.stderr)
        return 2

    full = "\n\n---\n\n".join(blocks)
    out = Path(a.out) if a.out else (path if path.is_dir() else path.parent) / "reanalise.md"
    out.write_text(full, encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
