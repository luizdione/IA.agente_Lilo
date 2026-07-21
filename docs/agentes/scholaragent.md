# ScholarAgent — Busca e síntese de literatura científica

Subagente do LILO (`agents/scholaragent/agent.py`, classe `ScholarAgent`,
`name = "scholar"`) que **busca artigos científicos** em fontes públicas e os
**sintetiza** com um LLM local. É um agente `BaseAgent` — roda dentro do LILO
(orquestrador ou pipeline Villa Lobos), **não** é um app web standalone.

> Nota: a versão antiga (app Flask de upload/análise de PDF com LLaVA) foi
> arquivada em `_ARCHIVE_v10/`. Para ler/extrair conteúdo de PDFs hoje, use o
> subagente **PDFs_library** (`pdf`).

## Fontes (APIs públicas)

- **PubMed** (E-utilities) e **arXiv** — nativos no agente
- Via `shared/research_sources.py`:
  - **OpenAlex** — 250M+ trabalhos; **substituto programático do Google
    Scholar** (que não tem API e bloqueia scraping) — V12.2
  - **Europe PMC** — PubMed + preprints + patentes + texto completo — V12.2
  - **Google Books** — livros (API v1; defina `GOOGLE_BOOKS_API_KEY` p/ uso
    confiável — a quota anônima satura com 429) — V12.2
  - **Wikipedia** — conhecimento geral (idioma via `LILO_WIKI_LANG`) — V12.2
  - **CrossRef**, **Semantic Scholar**, **ClinicalTrials.gov**,
    **Open Targets**, **NPI Registry** — V10.4

> Chaves OPCIONAIS (melhoram limites, não obrigatórias): `NCBI_API_KEY`,
> `SEMANTIC_SCHOLAR_API_KEY`, `GOOGLE_BOOKS_API_KEY`, `LILO_RESEARCH_EMAIL`.

## Tools expostas (`get_tools`)

| Tool | Função |
|------|--------|
| `scholar_search` | Busca artigos por tema. Params: `query` (obrigatório), `source`, `max_results` (padrão 5). |
| `scholar_synthesize` | Busca **e** sintetiza criticamente via LLM. Params: `query` (obrigatório), `max_results`. |
| `scholar_review` (V13.1) | **Revisão de literatura** estruturada: busca ampla multi-fonte + dedup (DOI/título) + estado da arte/consensos/lacunas/direções, com refs reais `[n]`. Params: `query` (obrigatório), `max_results` (padrão 20). Escritor `LILO_REVIEW_MODEL` (default cloud `gpt-oss:120b-cloud`, sem GPU). |

`source` aceita: `auto` (padrão: PubMed + arXiv), `all` (agrega todas),
`pubmed`, `arxiv`, `clinicaltrials`, `opentargets`, `npi`, `crossref`,
`semanticscholar`.

## Comportamento (`run`)

1. Sanitiza a query e resolve `source`/`max_results`/`synthesize` do contexto.
2. Consulta as fontes selecionadas (PubMed/arXiv nativos; demais via
   `research_sources`); `source="all"` busca cobertura máxima.
3. Formata os resultados (título, autores, ano, fonte, URL).
4. Se `synthesize=True` (padrão), gera uma **síntese crítica** (tendências,
   consensos, lacunas) com o LLM local; senão, devolve só a lista formatada.

## Características de roteamento

- `cost_tier = "ollama"` (síntese 100% local), `local_only = True`,
  `latency_class = "slow"` (I/O de rede com as APIs externas).
- `KEYWORDS` (pubmed, arxiv, literatura, papers, ensaio clínico, open targets,
  crossref, DOI, etc.) alimentam o roteamento do Villa Lobos / `_detect_domain`
  para o domínio `scholar`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("scholar_synthesize",
                       {"query": "CRISPR base editing off-target", "max_results": 5}))
```

Ou pela aba **Scholar** do dashboard (`dashboard.py`, porta 8100), ou via MCP
(`lilo_scholar`).
