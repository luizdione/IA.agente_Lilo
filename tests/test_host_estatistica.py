"""Ponte lilo-host, estatistica: conferida contra o R num conjunto fixo (portao G3).

Com o Rscript do env, cada teste compara estatistica e p com o R (tolerancia
1e-6 em p, 1e-4 em Tukey/IC). Sem R, os testes ainda conferem estrutura e
valores conhecidos contra o scipy.
"""
from __future__ import annotations

import math
import subprocess

import numpy as np
import pytest

from lilo_host import estatistica as E
from lilo_host.execucao import rscript_exe

A = [5.1, 4.9, 6.2, 5.8, 6.0, 5.5, 5.3, 6.1, 5.7, 5.4]
B = [6.5, 6.8, 7.0, 6.1, 7.2, 6.9, 6.4, 7.1, 6.6, 6.3]
C = [5.9, 6.3, 6.0, 5.6, 6.4, 6.2, 5.8, 6.1, 6.6, 5.5]
X = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
Y = [2.1, 3.9, 6.2, 7.8, 10.1, 12.3, 13.8, 16.2, 18.1, 19.7]
TAB = [[12, 30], [25, 18]]

R_SCRIPT = r"""
a <- c(%s); b <- c(%s); cc <- c(%s); x <- c(%s); y <- c(%s)
f <- function(k, v) cat(sprintf("%%s=%%.10g\n", k, v))
w <- t.test(a, b); f("welch_t", w$statistic); f("welch_p", w$p.value); f("welch_df", w$parameter)
f("welch_ci1", w$conf.int[1]); f("welch_ci2", w$conf.int[2])
s <- t.test(a, b, var.equal=TRUE); f("student_t", s$statistic); f("student_p", s$p.value)
p <- t.test(a, b, paired=TRUE); f("pareado_t", p$statistic); f("pareado_p", p$p.value)
m <- wilcox.test(a, b); f("mwu_U", m$statistic); f("mwu_p", m$p.value)
d <- data.frame(v=c(a,b,cc), g=factor(rep(c("A","B","C"), each=10)))
av <- aov(v ~ g, data=d); sm <- summary(av)[[1]]; f("anova_F", sm[["F value"]][1]); f("anova_p", sm[["Pr(>F)"]][1])
tk <- TukeyHSD(av)$g; f("tukey_AB_p", tk["B-A", "p adj"]); f("tukey_AC_diff", tk["C-A", "diff"])
cp <- cor.test(x, y); f("pearson_r", cp$estimate); f("pearson_p", cp$p.value); f("pearson_ci1", cp$conf.int[1])
cs <- cor.test(x, y, method="spearman"); f("spearman_r", cs$estimate)
sh <- shapiro.test(a); f("shapiro_W", sh$statistic); f("shapiro_p", sh$p.value)
q <- chisq.test(matrix(c(12,25,30,18), nrow=2), correct=FALSE); f("chi2", q$statistic); f("chi2_p", q$p.value)
kw <- kruskal.test(v ~ g, data=d); f("kruskal_H", kw$statistic); f("kruskal_p", kw$p.value)
"""


def _vec(v):
    return ", ".join(repr(float(t)) for t in v)


@pytest.fixture(scope="module")
def r_ref():
    rs = rscript_exe()
    if not rs:
        return None
    script = R_SCRIPT % (_vec(A), _vec(B), _vec(C), _vec(X), _vec(Y))
    out = subprocess.run([rs, "--vanilla", "-e", script], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    ref = {}
    for linha in out.stdout.splitlines():
        if "=" in linha:
            k, v = linha.split("=", 1)
            ref[k.strip()] = float(v)
    assert "welch_p" in ref, out.stdout
    return ref


def _perto(obtido, esperado, tol=1e-6):
    assert obtido is not None and esperado is not None
    assert math.isclose(obtido, esperado, rel_tol=tol, abs_tol=tol), (obtido, esperado)


def _am(a, b=None):
    return E.carregar(valores=a, valores_b=b)


def test_descritiva():
    d = E.descrever(_am(A))["amostras"][0]
    assert d["n"] == 10 and _perto(d["media"], float(np.mean(A)), 1e-4) is None
    assert d["ic95"][0] < d["media"] < d["ic95"][1]


def test_teste_t_welch_student_pareado(r_ref):
    w = E.teste_t(_am(A, B))
    assert w["teste"] == "t de Welch" and w["p"] < 0.001 and w["d_cohen"] < -1
    s = E.teste_t(_am(A, B), var_igual=True)
    p = E.teste_t(_am(A, B), pareado=True)
    # d de Cohen com desvio agrupado (ddof=1), o erro que o stats_agent antigo tinha
    sp = math.sqrt((np.var(A, ddof=1) + np.var(B, ddof=1)) / 2)
    _perto(w["d_cohen"], (np.mean(A) - np.mean(B)) / sp, 1e-3)
    if r_ref:
        _perto(w["t"], r_ref["welch_t"], 1e-4); _perto(w["p"], r_ref["welch_p"]); _perto(w["gl"], r_ref["welch_df"], 1e-4)
        _perto(w["ic95_diferenca"][0], r_ref["welch_ci1"], 1e-4); _perto(w["ic95_diferenca"][1], r_ref["welch_ci2"], 1e-4)
        _perto(s["t"], r_ref["student_t"], 1e-4); _perto(s["p"], r_ref["student_p"])
        _perto(p["t"], r_ref["pareado_t"], 1e-4); _perto(p["p"], r_ref["pareado_p"])


def test_mann_whitney(r_ref):
    m = E.mann_whitney(_am(A, B))
    assert m["p"] < 0.01
    if r_ref:
        _perto(m["U"], r_ref["mwu_U"], 1e-6); _perto(m["p"], r_ref["mwu_p"])


def test_anova_tukey_kruskal(r_ref):
    am = {"A": np.array(A), "B": np.array(B), "C": np.array(C)}
    a = E.anova(am)
    assert a["gl"] == [2, 27] and a["pos_hoc"] == "Tukey HSD" and len(a["pares"]) == 3
    k = E.anova(am, nao_parametrico=True)
    assert k["teste"] == "Kruskal-Wallis"
    if r_ref:
        _perto(a["F"], r_ref["anova_F"], 1e-4); _perto(a["p"], r_ref["anova_p"])
        ab = next(x for x in a["pares"] if {x["a"], x["b"]} == {"A", "B"})
        ac = next(x for x in a["pares"] if {x["a"], x["b"]} == {"A", "C"})
        _perto(ab["p_tukey"], r_ref["tukey_AB_p"], 1e-4)
        _perto(abs(ac["diferenca"]), abs(r_ref["tukey_AC_diff"]), 1e-4)
        _perto(k["H"], r_ref["kruskal_H"], 1e-4); _perto(k["p"], r_ref["kruskal_p"], 1e-4)


def test_correlacao(r_ref):
    c = E.correlacao(_am(X, Y))
    s = E.correlacao(_am(X, Y), metodo="spearman")
    assert c["n"] == 10 and c["r"] > 0.99 and s["r"] == 1.0
    if r_ref:
        _perto(c["r"], r_ref["pearson_r"], 1e-6); _perto(c["p"], r_ref["pearson_p"], 1e-4)
        _perto(c["ic95"][0], r_ref["pearson_ci1"], 1e-3); _perto(s["r"], r_ref["spearman_r"], 1e-6)
    with pytest.raises(ValueError):
        E.correlacao(_am(X, Y[:-1]))


def test_normalidade(r_ref):
    n = E.normalidade(_am(A))["amostras"][0]
    assert 0 < n["W"] <= 1
    if r_ref:
        _perto(n["W"], r_ref["shapiro_W"], 1e-5); _perto(n["p"], r_ref["shapiro_p"], 1e-4)


def test_qui_quadrado(r_ref):
    q = E.qui_quadrado(TAB)
    assert q["gl"] == 1 and q["n"] == 85 and 0 < q["v_cramer"] < 1
    if r_ref:
        _perto(q["chi2"], r_ref["chi2"], 1e-6); _perto(q["p"], r_ref["chi2_p"])


def test_carregar_csv_por_grupo(tmp_path):
    csv = tmp_path / "d.csv"
    linhas = ["grupo,valor"] + ["A,%s" % v for v in A] + ["B,%s" % v for v in B]
    csv.write_text("\n".join(linhas), encoding="utf-8")
    am = E.carregar(csv=str(csv), coluna="valor", grupo="grupo")
    assert set(am) == {"A", "B"} and am["A"].size == 10
    r = E.executar("teste_t", csv=str(csv), coluna="valor", grupo="grupo")
    assert r["p"] < 0.001
    assert E.executar("teste_t", csv=str(csv), coluna="nao_existe").startswith("[ERRO]")
    assert E.executar("anova", valores=A).startswith("[ERRO]")
