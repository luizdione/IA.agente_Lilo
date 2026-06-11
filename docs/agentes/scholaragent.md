# ScholarAgent — Busca e síntese de literatura científica

Subagente do LILO (`agents/scholaragent/agent.py`, classe `ScholarAgent`,
`name = "scholar"`) que **busca artigos científicos** em fontes públicas e os
**sintetiza** com um LLM local. É um agente `BaseAgent` — roda dentro do LILO
(orquestrador ou pipeline Villa Lobos), **não** é um app web standalone.

> Nota: a versão antiga (app Flask de upload/análise de PDF com LLaVA) foi
> arquivada em `_ARCHIVE_v10/`. Para ler/extrair conteúdo de PDFs hoje, use o
> subagente **PDFs_library** (`pdf`).

## Fontes (todas APIs públicas, sem chave)

- **PubMed** (E-utilities) — nativo no agente
- **arXiv** (API pública) — nativo no agente
- **ClinicalTrials.gov**, **Open Targets**, **NPI Registry**, **CrossRef**,
  **Semantic Scholar** — via `shared/research_sources.py` (V10.4)

## Tools expostas (`get_tools`)

| Tool | Função |
|------|--------|
| `scholar_search` | Busca artigos por tema. Params: `query` (obrigatório), `source`, `max_results` (padrão 5). |
| `scholar_synthesize` | Busca **e** sintetiza criticamente via LLM. Params: `query` (obrigatório), `max_results`. |

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
