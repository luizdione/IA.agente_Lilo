---
name: prism_audit
description: "Auditar análise estatística existente: verificar pressupostos violados, p-hacking, tamanho amostral, reprodutibilidade. Use quando o usuário quer validar uma análise já feita ou revisar resultados estatísticos de um paper. Triggers: 'auditar analise', 'verificar estatistica', 'prism audit', 'revisar resultados', 'pressupostos violados', 'p-hacking', 'tamanho amostral', 'validar analise', 'checar metodos estatisticos'."
---

# Prism AI — Auditoria Estatística

## Função
Valida uma análise estatística existente: verifica pressupostos, detecta problemas metodológicos, avalia poder estatístico e reprodutibilidade.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python -c "
import sys; sys.path.insert(0, '.')
from agents.prism_ai.stats_agent import StatsAgent
agent = StatsAgent()
# Auditar resultados existentes
result = agent.audit('<descricao_da_analise>', data_file='<arquivo.xlsx>')
print(result)
"
```

## Checklist de auditoria

### 1. Pressupostos do teste
- [ ] Normalidade verificada (Shapiro-Wilk / KS)?
- [ ] Homocedasticidade verificada (Levene / Bartlett)?
- [ ] Independência das amostras garantida?
- [ ] Outliers identificados e justificados?

### 2. Escolha do teste
- [ ] Teste paramétrico com dados não-normais?
- [ ] ANOVA sem post-hoc quando necessário?
- [ ] Comparações múltiplas sem correção (Bonferroni/FDR)?
- [ ] n adequado para o teste escolhido?

### 3. Poder estatístico
- [ ] Cálculo de n amostral pré-estudo (power analysis)?
- [ ] Effect size reportado (Cohen's d, η², r)?
- [ ] Intervalo de confiança (95% CI) reportado?

### 4. Reprodutibilidade
- [ ] Versão do software/pacote reportada?
- [ ] Seed fixada para análises com aleatoriedade?
- [ ] Dados brutos disponíveis?

## Passos
1. Peça ao usuário: descrição da análise, arquivo de dados, resultados reportados.
2. Execute verificação de pressupostos nos dados brutos (se disponíveis).
3. Gere relatório de auditoria com problemas encontrados e recomendações.
4. Se houver violações, sugira teste alternativo via `/prism_classify`.
5. Calcule poder estatístico post-hoc se n for pequeno (< 30/grupo).

## Outputs
- Relatório de auditoria em Markdown
- Lista de problemas críticos vs. menores
- Recomendações metodológicas
- Texto para seção "Análise Estatística" corrigida
