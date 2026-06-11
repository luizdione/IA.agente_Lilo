---
name: lilo_scholar
description: "Busca acadêmica científica com LILO. Use para buscar artigos em PubMed, arXiv, Scholar; gerar referências; encontrar papers sobre um tema. Triggers: 'buscar artigos', 'pubmed', 'arxiv', 'literatura cientifica', 'referencias', 'papers sobre', 'lilo scholar', 'pesquisa academica', 'publicacoes', 'scholar'."
---

# LILO Scholar — Busca Acadêmica Científica

## Função
Roteia para `agents/scholaragent/agent.py` — busca em bases científicas (PubMed, arXiv, CrossRef), formatação de referências e análise de papers.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py scholar "<query de busca>"
```

Exemplos:
```bash
python lilo.py scholar "CRISPR Trypanosoma cruzi 2024"
python lilo.py scholar "inibidores TcTR bovinos tratamento"
python lilo.py scholar "single-cell RNA-seq Leishmania"
```

## Fontes de busca
- **PubMed/NCBI** — literatura biomédica
- **arXiv** — preprints (física, computação, bio)
- **CrossRef** — metadados e DOI
- **Semantic Scholar** — citações e relevância

## Passos
1. Receba o tema/query de busca do usuário.
2. Execute `python lilo.py scholar "<query>"`.
3. Apresente resultados com: título, autores, ano, DOI/PMID, abstract.
4. Formate referências no estilo solicitado (ABNT, Vancouver, APA).
5. Destaque papers mais relevantes e recentes (≤3 anos).

## Capacidades extras
- Formatação automática de referências bibliográficas
- Filtro por ano, journal, tipo (review, research article)
- Extração e análise de PDFs dos artigos encontrados (integra com lilo_pdf)
- Sugestão de termos MeSH para refinar busca

## Nota
Para buscas mais profundas com MCP do PubMed/bioRxiv disponíveis no Cowork, combine com os conectores `mcp__ee283602` (PubMed) e `mcp__0c4ccedf`/`mcp__1d078ed1` (bioRxiv).
