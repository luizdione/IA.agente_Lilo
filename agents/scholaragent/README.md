# scholaragent — Subagente de busca de literatura (LILO)

`ScholarAgent` (`agent.py`) é um subagente `BaseAgent` que **busca e sintetiza
literatura científica**. Roda dentro do LILO — não é um app web standalone.

- **Fontes (públicas, sem chave):** PubMed, arXiv (nativos) + ClinicalTrials.gov,
  Open Targets, NPI Registry, CrossRef, Semantic Scholar (via
  `shared/research_sources.py`).
- **Tools:** `scholar_search` (lista artigos) e `scholar_synthesize` (lista +
  síntese crítica via LLM local).
- **Síntese:** 100% local (Ollama), em português, registro técnico.

Documentação completa: [`docs/agentes/scholaragent.md`](../../docs/agentes/scholaragent.md).

```python
from agents.scholaragent.agent import ScholarAgent
print(ScholarAgent().run("docking molecular SARS-CoV-2 Mpro",
                         {"source": "all", "max_results": 5}))
```

> Histórico: a versão anterior (app Flask de análise de PDF com LLaVA) foi
> arquivada em `_ARCHIVE_v10/`. Para PDFs, use o subagente `PDFs_library`.
