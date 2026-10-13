"""Estatistica sobre pingouin/statsmodels/scipy (grupo analise).

Entrada de cada teste: listas de numeros OU um CSV (`csv` + `coluna`, opcionalmente
`grupo` para separar as amostras). Saida: dict serializavel com estatistica, p,
tamanho de efeito, n e IC, mais um `resumo` em uma linha em portugues.

O `stats_agent.py` da arch-v11 NAO foi reaproveitado (d de Cohen com ddof=0,
pos-teste inadequado). Aqui o d de Cohen e o do pingouin (desvio agrupado, ddof=1)
e o pos-teste da ANOVA e Tukey HSD. Conferido contra o R em tests/test_host_estatistica.py.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .comum import erro, resolver


def _num(x: Any) -> np.ndarray:
    a = pd.to_numeric(pd.Series(list(x)), errors="coerce").dropna().to_numpy(dtype=float)
    if a.size == 0:
        raise ValueError("amostra vazia ou nao numerica")
    return a


def carregar(csv: str = "", coluna: str = "", grupo: str = "",
             valores: list[float] | None = None,
             valores_b: list[float] | None = None) -> dict[str, np.ndarray]:
    """{rotulo -> amostra}. Prioridade: CSV (coluna [+grupo]) > listas inline."""
    if csv:
        p = resolver(csv)
        if not p.is_file():
            raise FileNotFoundError("CSV nao existe: %s" % p)
        df = pd.read_csv(p, sep=None, engine="python")
        if coluna not in df.columns:
            raise KeyError("coluna '%s' nao existe; colunas: %s" % (coluna, list(df.columns)))
        if grupo:
            if grupo not in df.columns:
                raise KeyError("coluna de grupo '%s' nao existe" % grupo)
            return {str(g): _num(sub[coluna]) for g, sub in df.groupby(grupo, sort=True)}
        return {coluna: _num(df[coluna])}
    out = {}
    if valores is not None:
        out["a"] = _num(valores)
    if valores_b is not None:
        out["b"] = _num(valores_b)
    if not out:
        raise ValueError("passe `csv`+`coluna` ou `valores` (e `valores_b`)")
    return out


def _r(x: float, nd: int = 6) -> float | None:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), nd)


def _p(p: float) -> str:
    return "p < 0,001" if p < 0.001 else "p = %.3f" % p


def descrever(amostras: dict[str, np.ndarray]) -> dict:
    """Media, DP, EP, mediana, quartis, min, max, IC95% da media, n."""
    from scipy import stats
    linhas = []
    for nome, a in amostras.items():
        n = a.size
        m, sd = a.mean(), a.std(ddof=1) if n > 1 else 0.0
        ep = sd / math.sqrt(n) if n > 1 else 0.0
        t = stats.t.ppf(0.975, n - 1) if n > 1 else float("nan")
        linhas.append({"amostra": nome, "n": int(n), "media": _r(m), "dp": _r(sd), "ep": _r(ep),
                       "ic95": [_r(m - t * ep), _r(m + t * ep)] if n > 1 else None,
                       "mediana": _r(np.median(a)), "q1": _r(np.percentile(a, 25)),
                       "q3": _r(np.percentile(a, 75)), "min": _r(a.min()), "max": _r(a.max())})
    return {"teste": "descritiva", "amostras": linhas}


def normalidade(amostras: dict[str, np.ndarray]) -> dict:
    """Shapiro-Wilk por amostra (+ assimetria e curtose)."""
    import pingouin as pg
    from scipy import stats
    linhas = []
    for nome, a in amostras.items():
        r = pg.normality(a, method="shapiro").iloc[0]
        linhas.append({"amostra": nome, "n": int(a.size), "W": _r(r["W"]), "p": _r(r["pval"], 8),
                       "normal_a_5pct": bool(r["normal"]), "assimetria": _r(stats.skew(a)),
                       "curtose": _r(stats.kurtosis(a))})
    return {"teste": "Shapiro-Wilk", "amostras": linhas,
            "resumo": "; ".join("%s: W=%.3f, %s" % (l["amostra"], l["W"], _p(l["p"])) for l in linhas)}


def _duas(amostras: dict[str, np.ndarray]) -> tuple[str, np.ndarray, str, np.ndarray]:
    if len(amostras) != 2:
        raise ValueError("o teste precisa de exatamente 2 amostras (tem %d)" % len(amostras))
    (ra, a), (rb, b) = amostras.items()
    return ra, a, rb, b


def _ic_t(centro: float, se: float, gl: float) -> list:
    from scipy import stats
    t = stats.t.ppf(0.975, gl)
    return [_r(centro - t * se), _r(centro + t * se)]


def teste_t(amostras: dict[str, np.ndarray], pareado: bool = False, var_igual: bool = False) -> dict:
    """t de Student/Welch (padrao Welch) ou pareado; d de Cohen com sinal e IC95% da diferenca.

    O pingouin arredonda o IC a 2 casas e devolve |d|; aqui o IC e o d sao
    calculados direto (desvio agrupado com ddof=1; no pareado, DP das diferencas).
    """
    import pingouin as pg
    ra, a, rb, b = _duas(amostras)
    if pareado and a.size != b.size:
        raise ValueError("teste pareado exige amostras do mesmo tamanho")
    r = pg.ttest(a, b, paired=pareado, correction=(not var_igual) if not pareado else False).iloc[0]
    nome = "t pareado" if pareado else ("t de Student" if var_igual else "t de Welch")
    na, nb = a.size, b.size
    if pareado:
        dif = a - b
        se = dif.std(ddof=1) / math.sqrt(na)
        d = dif.mean() / dif.std(ddof=1) if dif.std(ddof=1) else float("nan")
        ic = _ic_t(dif.mean(), se, na - 1)
    else:
        sp2 = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
        d = (a.mean() - b.mean()) / math.sqrt(sp2) if sp2 else float("nan")
        se = math.sqrt(a.var(ddof=1) / na + b.var(ddof=1) / nb) if not var_igual else math.sqrt(sp2 * (1 / na + 1 / nb))
        ic = _ic_t(a.mean() - b.mean(), se, float(r["dof"]))
    return {"teste": nome, "amostras": {ra: int(na), rb: int(nb)},
            "media_a": _r(a.mean()), "media_b": _r(b.mean()), "diferenca": _r(a.mean() - b.mean()),
            "t": _r(r["T"]), "gl": _r(r["dof"]), "p": _r(r["p_val"], 8), "ic95_diferenca": ic,
            "d_cohen": _r(d), "poder": _r(r["power"]),
            "resumo": "%s: t(%s) = %.3f, %s, d = %.2f" % (nome, _r(r["dof"], 2), r["T"], _p(r["p_val"]), d)}


def mann_whitney(amostras: dict[str, np.ndarray]) -> dict:
    """Mann-Whitney U (bilateral; exato quando possivel) com correlacao bisserial."""
    import pingouin as pg
    ra, a, rb, b = _duas(amostras)
    r = pg.mwu(a, b, alternative="two-sided").iloc[0]
    return {"teste": "Mann-Whitney U", "amostras": {ra: int(a.size), rb: int(b.size)},
            "mediana_a": _r(np.median(a)), "mediana_b": _r(np.median(b)),
            "U": _r(r["U_val"]), "p": _r(r["p_val"], 8), "rbc": _r(r["RBC"]), "cles": _r(r["CLES"]),
            "resumo": "Mann-Whitney: U = %.1f, %s, r = %.2f" % (r["U_val"], _p(r["p_val"]), r["RBC"])}


def anova(amostras: dict[str, np.ndarray], nao_parametrico: bool = False) -> dict:
    """ANOVA de uma via (+ Tukey HSD) ou Kruskal-Wallis (+ Dunn/Holm, via pos-hoc de postos)."""
    import pingouin as pg
    if len(amostras) < 2:
        raise ValueError("ANOVA precisa de 2+ grupos")
    df = pd.DataFrame([(g, v) for g, arr in amostras.items() for v in arr], columns=["grupo", "valor"])
    if nao_parametrico:
        r = pg.kruskal(data=df, dv="valor", between="grupo").iloc[0]
        pos = pg.pairwise_tests(data=df, dv="valor", between="grupo", parametric=False, padjust="holm")
        pares = [{"a": x["A"], "b": x["B"], "U": _r(x["U_val"]), "p_ajustado": _r(x["p_corr"], 8)}
                 for _, x in pos.iterrows()]
        return {"teste": "Kruskal-Wallis", "grupos": {g: int(a.size) for g, a in amostras.items()},
                "H": _r(r["H"]), "gl": int(r["ddof1"]), "p": _r(r["p_unc"], 8), "pos_hoc": "Mann-Whitney + Holm",
                "pares": pares, "resumo": "Kruskal-Wallis: H(%d) = %.3f, %s" % (r["ddof1"], r["H"], _p(r["p_unc"]))}
    r = pg.anova(data=df, dv="valor", between="grupo", detailed=True)
    efeito = r.iloc[0]
    tk = pg.pairwise_tukey(data=df, dv="valor", between="grupo")
    pares = [{"a": x["A"], "b": x["B"], "diferenca": _r(x["diff"]), "p_tukey": _r(x["p_tukey"], 8),
              "hedges_g": _r(x["hedges"])} for _, x in tk.iterrows()]
    return {"teste": "ANOVA de uma via", "grupos": {g: int(a.size) for g, a in amostras.items()},
            "F": _r(efeito["F"]), "gl": [int(efeito["DF"]), int(r.iloc[1]["DF"])], "p": _r(efeito["p_unc"], 8),
            "eta2_parcial": _r(efeito["np2"]), "pos_hoc": "Tukey HSD", "pares": pares,
            "resumo": "ANOVA: F(%d, %d) = %.3f, %s, eta2p = %.2f" % (
                efeito["DF"], r.iloc[1]["DF"], efeito["F"], _p(efeito["p_unc"]), efeito["np2"])}


def correlacao(amostras: dict[str, np.ndarray], metodo: str = "pearson") -> dict:
    """Pearson ou Spearman entre duas series pareadas (mesmo n), com IC95%."""
    import pingouin as pg
    ra, a, rb, b = _duas(amostras)
    if a.size != b.size:
        raise ValueError("series de tamanhos diferentes (%d vs %d)" % (a.size, b.size))
    metodo = metodo.lower()
    if metodo not in ("pearson", "spearman", "kendall"):
        raise ValueError("metodo: pearson | spearman | kendall")
    r = pg.corr(a, b, method=metodo).iloc[0]
    from scipy import stats
    n = int(r["n"])
    z, sez = math.atanh(max(-0.999999, min(0.999999, float(r["r"])))), 1 / math.sqrt(max(n - 3, 1))
    q = stats.norm.ppf(0.975)
    ci = [math.tanh(z - q * sez), math.tanh(z + q * sez)]
    return {"teste": "correlacao de %s" % metodo.capitalize(), "x": ra, "y": rb, "n": int(r["n"]),
            "r": _r(r["r"]), "ic95": [_r(ci[0]), _r(ci[1])], "p": _r(r["p_val"], 8),
            "r2": _r(r["r"] ** 2), "resumo": "%s: r = %.3f [%.2f, %.2f], %s, n = %d" % (
                metodo.capitalize(), r["r"], ci[0], ci[1], _p(r["p_val"]), r["n"])}


def qui_quadrado(tabela: list[list[float]], yates: bool = False) -> dict:
    """Qui-quadrado de independencia numa tabela de contingencia (linhas x colunas) + V de Cramer."""
    from scipy import stats
    obs = np.asarray(tabela, dtype=float)
    if obs.ndim != 2 or obs.shape[0] < 2 or obs.shape[1] < 2:
        raise ValueError("a tabela precisa ter ao menos 2 linhas e 2 colunas")
    chi2, p, gl, esperado = stats.chi2_contingency(obs, correction=yates)
    n = obs.sum()
    v = math.sqrt(chi2 / (n * (min(obs.shape) - 1))) if n else float("nan")
    aviso = "" if (esperado >= 5).all() else " (atencao: ha esperados < 5; considere Fisher)"
    return {"teste": "qui-quadrado de independencia", "chi2": _r(chi2), "gl": int(gl), "p": _r(p, 8),
            "n": int(n), "v_cramer": _r(v), "esperados_min": _r(esperado.min()),
            "resumo": "chi2(%d, N=%d) = %.3f, %s, V = %.2f%s" % (gl, n, chi2, _p(p), v, aviso)}


def executar(teste: str, **kw) -> dict | str:
    """Despacho usado pelo servidor: nome do teste + argumentos de `carregar` e do teste."""
    try:
        amostras = carregar(kw.pop("csv", ""), kw.pop("coluna", ""), kw.pop("grupo", ""),
                            kw.pop("valores", None), kw.pop("valores_b", None))
        fn = {"descrever": descrever, "normalidade": normalidade, "teste_t": teste_t,
              "mann_whitney": mann_whitney, "anova": anova, "correlacao": correlacao}[teste]
        return fn(amostras, **kw)
    except (ValueError, KeyError, FileNotFoundError) as e:
        return erro(str(e))
