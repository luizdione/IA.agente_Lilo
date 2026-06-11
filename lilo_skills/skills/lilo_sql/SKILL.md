---
name: lilo_sql
description: "Análise SQL e estatística com LILO. Use para queries SQL, análise de banco de dados SQLite/MySQL/PostgreSQL, estatísticas descritivas, ANOVA, t-test, correlações. Triggers: 'sql', 'query', 'SELECT', 'tabela', 'banco de dados', 'database', 'estatistica sql', 'analisar dados sql', 'lilo sql'."
---

# LILO SQL — Análise SQL e Estatística

## Função
Roteia para `agents/Analise_SQL/agent.py` — análise de banco de dados, queries otimizadas, estatística descritiva e inferencial em dados tabulares.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py sql "<query>"
```

Exemplos:
```bash
python lilo.py sql "liste as tabelas do banco"
python lilo.py sql "SELECT COUNT(*) FROM genomas WHERE especie='Trypanosoma'"
python lilo.py sql "faça ANOVA dos grupos experimentais na tabela resultados"
```

## Capacidades
- Queries SQL (SQLite, MySQL, PostgreSQL)
- Estatística descritiva (média, DP, mediana, IQR)
- Testes: t-test, ANOVA, Mann-Whitney, Kruskal-Wallis
- Correlações (Pearson, Spearman)
- Exportação de resultados

## Passos
1. Receba a query/pergunta do usuário.
2. Execute `python lilo.py sql "<query>"` via bash.
3. Se precisar de arquivo de banco, peça o caminho ao usuário.
4. Apresente resultados com interpretação estatística técnica.
5. Sugira queries complementares quando relevante.

## Nota
Para análise visual/gráfica de dados estatísticos, considere usar `/prism_analyze`.
