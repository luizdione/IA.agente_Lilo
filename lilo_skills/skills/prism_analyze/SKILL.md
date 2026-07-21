---
name: prism_analyze
description: "Análise estatística científica completa com Prism AI. Use para analisar dados experimentais, selecionar teste estatístico, gerar gráficos padrão publicação e exportar .pzfx (GraphPad Prism). Triggers: 'prism analyze', 'analisar experimento', 'estatistica cientifica', 'grafico publicacao', 'boxplot', 'comparar grupos', 'p-value', 'exportar pzfx', 'graphpad', 'dados experimentais'."
---

# Prism AI — Análise Estatística Científica Completa

## Função
Executa o pipeline completo do `agents/prism_ai`: ingestão de dados → classificação do experimento → seleção de teste estatístico → visualização → redação de resultados → exportação .pzfx.

## Pipeline
```
ingest → classify → stats → visualize → write → export
```

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py prism "<query>" 
```

Exemplos:
```bash
python lilo.py prism "analisar dados de expressão proteica entre 3 grupos tratamento"
python lilo.py prism "comparar viabilidade celular controle vs tratado, arquivo dados.xlsx"
```

## Passos
1. Solicite ao usuário o arquivo de dados (`.xlsx` ou `.csv`) se não fornecido.
2. Execute o pipeline Prism via `python lilo.py prism "<descricao>"`.
3. O agente irá:
   - **Ingerir** e validar os dados
   - **Classificar** o design experimental (1-way ANOVA, 2-way ANOVA, pareado, não-pareado, etc.)
   - **Verificar pressupostos** (normalidade Shapiro-Wilk, homocedasticidade Levene)
   - **Selecionar e executar** o teste estatístico adequado
   - **Gerar gráficos** (boxplot, barplot com SEM, violin plot) padrão publicação
   - **Redigir** seção Resultados em linguagem científica
   - **Exportar** `.pzfx` para GraphPad Prism
4. Apresente: estatística do teste, p-value, effect size (Cohen's d, η²), intervalos de confiança.
5. Informe se pressupostos foram violados e qual teste alternativo foi usado.

## Testes suportados
- Paramétricos: t-test, ANOVA 1/2-way, ANCOVA, t pareado
- Não-paramétricos: Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman
- Post-hoc: Tukey, Dunn, Bonferroni, Holm
- Correlação: Pearson, Spearman

## Outputs
- Tabela de resultados (estatística, p-value, effect size)
- Gráfico PNG (300 dpi, padrão journal)
- Arquivo `.pzfx` para GraphPad Prism
- Texto da seção Resultados (pronto para manuscrito)
