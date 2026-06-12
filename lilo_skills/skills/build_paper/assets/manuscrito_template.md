---
title: "TÍTULO INFORMATIVO E ESPECÍFICO (idealmente com o achado central)"
author:
  - "Sobrenome N.¹"
  - "[coautores a definir]"
date: "AAAA-MM-DD"
lang: en-US   # use "pt-BR" na versão de análise
abstract: |
  Síntese autocontida (contexto e lacuna -> objetivo -> abordagem ->
  principais resultados QUANTITATIVOS reais -> conclusão/implicação). Sem
  citações nem siglas não definidas. Respeite o teto do periódico-alvo
  (ex.: 250 palavras na Acta Tropica).
# header-includes carrega os pacotes usados pela marcação de auditoria no PDF
# (tectonic baixa sob demanda). Inofensivo na versão de submissão.
header-includes:
  - \usepackage{xcolor}
  - \usepackage{tcolorbox}
---

<!--
  CONVENÇÕES DE NOTAÇÃO (pandoc):
    *Espécie/gene* em itálico        -> *Trypanosoma cruzi*
    Sobrescrito / subscrito          -> Mg^2+^   10^-5^   H~2~O
    Símbolos                         -> ≤ ≥ ≈ × · Å µ (fonte Cambria cobre)
    Tabelas em pipe table do pandoc; seções numeradas (# 1., ## 2.1).
  VERSÃO PT DE ANÁLISE: rode marcar_versao_analise.py para inserir o banner
  vermelho e a caixa de pendências (NÃO os escreva à mão aqui).
-->

**Keywords:** termo1; termo2; termo3; termo4; termo5; termo6.

**Highlights**

- Bullet 1 (curto; respeite o limite de caracteres do periódico).
- Bullet 2.
- Bullet 3.

# 1. Introduction

Contextualize o tema e a relevância; estado da arte; lacuna de conhecimento;
justificativa; e, ao final, **objetivos e hipóteses explícitos**. Cada
afirmação não trivial é atribuída a uma fonte. (Meta de profundidade: ver
reference/estrutura_e_profundidade.md.)

# 2. Materials and Methods

## 2.1 [Materiais / amostras / organismos]
Detalhe o suficiente para reprodução: origem, critérios de inclusão/exclusão.

## 2.2 [Procedimentos experimentais / computacionais]
Protocolos, softwares, **versões e parâmetros**, bancos de dados e releases.

## 2.3 [Análise estatística / avaliação]
Testes, correção de múltiplas comparações, limiares, métricas. Reprodutível.

# 3. Results

Descreva os achados objetivamente, na ordem das figuras/tabelas, com **métricas
reais** extraídas dos dados-fonte. Sem interpretação excessiva. Toda figura/
tabela é citada no texto (Figura 1, Tabela 1) e vice-versa.

# 4. Discussion

Interprete criticamente; compare com a literatura (concordâncias e
divergências); proponha mecanismos; **declare limitações**; aponte estudos
futuros e aplicações. Profundidade igual ou superior à dos Resultados.

# 5. Conclusion

Sintetize os avanços centrais, alinhados aos resultados; sem extrapolações.

# Declarations

**Funding:** [a preencher]
**Conflict of interest:** [a preencher]
**Author contributions (CRediT):** [a preencher]
**Data and code availability:** [a preencher]
**Acknowledgements:** [a preencher]
**Ethics approval:** [se aplicável]

# References

[No estilo do periódico-alvo. Todas verificadas: autores, ano, periódico,
volume, páginas, DOI. Sem placeholders "[verificar]" na versão final.]
