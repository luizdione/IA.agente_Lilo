# 🧬 Analisador Estatístico de Dados SQL

Sistema autônomo de análise estatística para dados biológicos em bancos SQL.

## 🚀 Execução Rápida

```bash
# Windows
run_sql_analyzer.bat
```

**Na primeira execução**, o sistema instalará automaticamente todas as dependências necessárias.

## 📋 Requisitos

- Python 3.8+
- Conexão com internet (para instalar dependências na primeira vez)

## 🔗 Conexão com Banco de Dados

### Servidores Pré-configurados:

1. **Servidor Hostinger**
   - Host: `auth-db887.hstgr.io`
   - Banco: `u112348440_ifrj_crj_lgm`
   - Usuário: `u112348440_Desenvolvedor`

2. **Servidor Local/Remoto**
   - Host: `127.0.0.1`
   - Banco: `u112348440_cx120`
   - Usuário: `u112348440_Darwin`

**Senhas já estão pré-configuradas.**

## 📊 Funcionalidades

### 🔍 **Camada 1: Inspeção de Dados**
- Análise automática da estrutura
- Identificação de tipos de variáveis
- Estatísticas descritivas completas
- Testes de normalidade e homogeneidade

### 💡 **Camada 2: Decisão Estatística**
- Recomendação automática de testes apropriados
- Árvore de decisão estatística
- Justificativa completa das escolhas

### 📈 **Camada 3: Execução e Visualização**
- Execução dos testes recomendados
- Geração automática de gráficos
- Relatórios completos formatados

## 🧪 Testes Suportados

- **Paramétricos:** Teste t, ANOVA, Teste t de Welch, ANOVA de Welch
- **Não-Paramétricos:** Mann-Whitney U, Kruskal-Wallis
- **Post-hoc:** Tukey HSD, Games-Howell, Dunn

## 📁 Estrutura de Arquivos

```
Analise_SQL/
├── sql_statistical_analyzer.py  # Módulo de análise (3 camadas)
├── sql_analyzer_gui.py           # Interface gráfica
├── run_sql_analyzer.bat          # Script de execução
├── requirements.txt              # Dependências
├── sql_analyzer_icon.ico         # Ícone do sistema
└── README.md                     # Esta documentação
```

## 🎯 Fluxo de Uso

1. **Executar** `run_sql_analyzer.bat`
2. **Selecionar** servidor preset (Hostinger ou Local)
3. **Conectar** ao banco de dados
4. **Carregar** dados (tabela ou query SQL)
5. **Selecionar** variáveis para análise
6. **Executar** análises (inspecionar/recomendar/executar)
7. **Visualizar** resultados na coluna direita

## 🔧 Dependências Principais

- `pandas` - Manipulação de dados
- `scipy` - Testes estatísticos
- `statsmodels` - Modelos avançados
- `matplotlib` / `seaborn` - Visualizações
- `customtkinter` - Interface gráfica moderna
- `mysql-connector-python` - Conexão MySQL

## 📝 Notas

- Sistema **100% autônomo** - não depende de LILO
- Senhas pré-configuradas para conveniência
- Interface em **2 colunas**: Controles (esquerda) + Resultados (direita)
- Barras de rolagem automáticas
- Instalação automática de dependências na primeira execução

## 🐛 Solução de Problemas

### "Python não encontrado"
- Instale Python 3.8+ de python.org
- Adicione Python ao PATH do Windows

### "Erro ao conectar ao banco"
- Verifique conexão com internet
- Confirme credenciais do servidor
- Teste com ferramenta externa (MySQL Workbench)

### "Falha ao instalar dependências"
- Execute: `python -m pip install --upgrade pip`
- Execute: `pip install -r requirements.txt`
- Verifique permissões de administrador

---

**Desenvolvido como consultor estatístico automatizado para pesquisa biológica**
