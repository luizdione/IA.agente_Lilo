# Prism AI — Análise Estatística Automatizada

**Path:** `agents/prism_ai/`
**Tools MCP:** `prism_analyze`, `prism_classify`, `prism_audit`, `prism_eda`

---

## O que faz

Análise científica completa de dados experimentais em `.xlsx` ou `.csv`. Inspirado no GraphPad Prism, mas open-source e automatizado.

Pipeline interno:

```
ingestion → classification → stats → visualization → writing → export
```

---

## Sub-agentes internos (6)

| Sub-agente | Função |
|---|---|
| `ingestion_agent` | Lê .xlsx/.csv, detecta colunas (grupos, valores, replicatas) |
| `classification_agent` | Classifica tipo de experimento (one-way ANOVA, two-way, regressão, etc.) |
| `stats_agent` | Aplica testes (Shapiro-Wilk, Levene, t-test, ANOVA, Mann-Whitney, Kruskal-Wallis, post-hoc) |
| `visualization_agent` | Gera gráficos publication-grade (matplotlib + seaborn) |
| `writing_agent` | Escreve seção "Resultados" em pt/en com p-values formatados |
| `export_agent` | Exporta como .docx, .png, .pdf |

---

## Tools

### `prism_analyze`

Análise completa em um único call.

| Arg | Default | Descrição |
|---|---|---|
| `file_path` | (obrigatório) | Caminho do .xlsx/.csv |
| `output_dir` | "" | Onde salvar resultados (default: pasta do arquivo) |
| `language` | "en" | Idioma do texto ("pt" ou "en") |
| `alpha` | 0.05 | Nível de significância |

### `prism_classify`

Detecta apenas o tipo de experimento.

### `prism_audit`

Audita uma análise existente, detecta erros (ex.: t-test em dados não-normais sem justificativa, ausência de teste post-hoc após ANOVA significativa).

### `prism_eda` (V13.3)

Perfil exploratório **rápido e determinístico** (sem LLM), antes do pipeline
pesado: dimensões, tipos/`%`nulos/cardinalidade por coluna, `describe` das
numéricas, histogramas (até 6) e heatmap de correlação (Pearson). Aciona por
`mode="eda"` ou query começando com `eda`/`perfil`/`profile`.

| Arg | Default | Descrição |
|---|---|---|
| `file_path` | (obrigatório) | Caminho do .xlsx/.csv |
| `output_dir` | "" | Onde salvar os PNGs (default: `<arquivo>/prism_output`) |

> Nomes de coluna são sanitizados para o filename dos gráficos (V11.4) — colunas
> com `/`, `:` etc. não quebram mais a geração no Windows.

---

## Decisões automáticas

- **Normalidade:** Shapiro-Wilk (n<50) ou Anderson-Darling (n≥50).
- **Homocedasticidade:** Levene.
- **Se normal + homo:** t-test ou ANOVA paramétrica.
- **Se não normal ou não homo:** Mann-Whitney ou Kruskal-Wallis.
- **Post-hoc após ANOVA significativa:** Tukey HSD ou Bonferroni.

---

## Saídas

- `analise.docx` — relatório formatado
- `figura_*.png` — gráficos individuais
- `figura_combined.pdf` — figura final pronta pra paper
- `stats.json` — output bruto dos testes
- `audit.md` — checklist de pressupostos

---

## Quando usar?

- Você tem dados experimentais e quer análise rápida correta.
- Quer auditar análise feita por outro (especialmente reviewers, alunos).
- Precisa gerar gráficos publication-grade rapidamente.

Para análise customizada multi-passo, prefira Villa-Lobos com Prism integrado.
