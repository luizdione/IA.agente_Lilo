---
name: prism_classify
description: "Classificar design experimental e selecionar teste estatístico adequado com Prism AI. Use quando o usuário quer saber qual teste usar, classificar o tipo de experimento, verificar se deve usar paramétrico ou não-paramétrico. Triggers: 'qual teste estatistico', 'classificar experimento', 'prism classify', 'design experimental', 'parametrico ou nao', 'qual anova', 'teste adequado', 'normalidade'."
---

# Prism AI — Classificação de Design Experimental

## Função
Usa o `ClassificationAgent` do Prism AI para determinar o tipo de experimento e selecionar o teste estatístico mais adequado, sem executar a análise completa.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python -c "
import sys; sys.path.insert(0, '.')
from agents.prism_ai.classification_agent import ClassificationAgent
agent = ClassificationAgent()
result = agent.classify('<descricao_do_experimento>')
print(result)
"
```

## Perguntas para coletar do usuário
Antes de classificar, obtenha:
1. **Número de grupos** — 2, 3 ou mais?
2. **Amostras** — independentes ou pareadas/repetidas?
3. **Variável dependente** — contínua, ordinal, categórica?
4. **Distribuição** — dados normais? Tamanho amostral?
5. **Fatores** — um fator (1-way) ou dois fatores (2-way)?

## Árvore de decisão resumida
```
Comparar 2 grupos?
  ├── Paramétrico, independente → t-test independente
  ├── Paramétrico, pareado    → t-test pareado
  ├── Não-param, independente → Mann-Whitney U
  └── Não-param, pareado      → Wilcoxon signed-rank

Comparar ≥3 grupos?
  ├── Paramétrico, 1 fator    → ANOVA 1-way + Tukey post-hoc
  ├── Paramétrico, 2 fatores  → ANOVA 2-way
  ├── Não-param, independente → Kruskal-Wallis + Dunn
  └── Não-param, repetidos    → Friedman + Wilcoxon post-hoc
```

## Passos
1. Colete as informações do design experimental do usuário.
2. Execute o ClassificationAgent com a descrição.
3. Apresente: teste recomendado, justificativa, pressupostos a verificar.
4. Ofereça executar a análise completa com `/prism_analyze`.

## Testes de pressuposto incluídos
- Shapiro-Wilk (normalidade, n < 50)
- Kolmogorov-Smirnov (normalidade, n ≥ 50)
- Levene (homocedasticidade)
- Bartlett (homocedasticidade, dados normais)
