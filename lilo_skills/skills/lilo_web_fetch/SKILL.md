---
name: lilo_web_fetch
description: "Fazer fetch do conteúdo completo de uma URL específica via LILO. Use para ler páginas web, abstracts de artigos, documentação online, páginas do PubMed, arXiv. Triggers: 'ler url', 'fetch pagina', 'lilo web fetch', 'abrir link', 'ler artigo online', 'conteudo da url', 'buscar conteudo pagina', 'scraping', 'baixar pagina'."
---

# LILO Web Fetch — Leitura de Páginas Web

## Função
Usa `shared/web_search.py:fetch_page()` para recuperar e parsear o conteúdo completo de uma URL, com limpeza de HTML e extração de texto.

## Como executar

```python
import sys; sys.path.insert(0, 'C:/Users/luizd/OneDrive/Data_Science/Projetos/IA.agente')
from shared.web_search import fetch_page

content = fetch_page("<url>")
print(content)
```

Ou diretamente via WebFetch do Cowork (preferido quando disponível):
```
WebFetch(url="<url>")
```

## URLs científicas úteis

```
# PubMed por PMID
https://pubmed.ncbi.nlm.nih.gov/<PMID>/

# arXiv por ID
https://arxiv.org/abs/<arxiv_id>

# DOI resolver
https://doi.org/<doi>

# UniProt proteína
https://www.uniprot.org/uniprot/<accession>

# NCBI Gene
https://www.ncbi.nlm.nih.gov/gene/<gene_id>

# Ensembl
https://ensembl.org/Homo_sapiens/Gene/Summary?g=<gene_id>
```

## Passos
1. Receba a URL do usuário (ou derive de PMID/DOI/arxiv_id).
2. Tente primeiro WebFetch do Cowork (método preferido).
3. Se falhar, use `fetch_page()` do módulo shared.
4. Extraia e apresente o conteúdo relevante (título, abstract, texto principal).
5. Para artigos científicos, estruture: título → autores → abstract → conclusão.
6. Ofereça análise mais profunda do conteúdo via `/lilo_pdf` se for PDF.

## Limitações
- Alguns sites bloqueiam scraping (Nature, Science full text — requer login)
- PDFs precisam de download local antes de análise profunda
- Conteúdo JavaScript-heavy pode não ser capturado (use Claude in Chrome nesses casos)

## Formatação do conteúdo
Após fetch, sempre:
1. Extraia o título da página
2. Identifique o tipo (abstract, documentação, blog, etc.)
3. Limpe elementos de navegação/publicidade
4. Apresente texto limpo e estruturado
