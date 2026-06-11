---
name: lilo_web_search
description: "Busca web científica via LILO (DuckDuckGo + fontes confiáveis). Use para buscar na internet, encontrar informações recentes, artigos científicos online, documentação. Triggers: 'buscar na web', 'pesquisar internet', 'lilo web search', 'duckduckgo', 'buscar online', 'encontrar artigo', 'pesquisar pubmed online', 'busca cientifica web'."
---

# LILO Web Search — Busca Web Científica

## Função
Usa `shared/web_search.py` para busca web via DuckDuckGo com priorização de domínios científicos confiáveis (PubMed, Nature, arXiv, UniProt, NCBI, etc.).

## Como executar

```python
# Via Python inline (preferido)
import sys; sys.path.insert(0, 'C:/Users/luizd/OneDrive/Data_Science/Projetos/IA.agente')
from shared.web_search import web_search, fetch_page

results = web_search("<query>", max_results=10, scientific=True)
for r in results:
    print(r['title'], r['url'])
    print(r['snippet'])
```

Ou usando o Cowork WebSearch diretamente para queries gerais.

## Domínios científicos priorizados
```
ncbi.nlm.nih.gov | pubmed | arxiv.org | nature.com | science.org
sciencedirect.com | springer.com | cell.com | plos.org
biorxiv.org | medrxiv.org | uniprot.org | rcsb.org
ensembl.org | ebi.ac.uk | bioconductor.org
```

## Passos
1. Receba a query de busca do usuário.
2. Determine se é busca científica (usar domínios priorizados) ou geral.
3. Execute a busca via `shared.web_search.web_search()` ou WebSearch do Cowork.
4. Filtre e ranqueie resultados por relevância e confiabilidade da fonte.
5. Apresente resultados com: título, URL, snippet e domínio.
6. Ofereça fazer fetch completo dos melhores resultados via `/lilo_web_fetch`.

## Estratégias de busca científica
- PubMed: prefixe com `site:pubmed.ncbi.nlm.nih.gov`
- arXiv: prefixe com `site:arxiv.org`
- Genérica científica: adicione "ncbi OR pubmed OR nature" à query
- Código/bioinformática: adicione "github OR bioconductor OR pypi"

## Nota
Para buscar artigos e obter metadados completos (PMID, DOI, abstract), prefira `/lilo_scholar` que usa APIs estruturadas (não scraping).
