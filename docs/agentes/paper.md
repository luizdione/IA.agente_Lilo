# PaperAgent — Redação científica (skill `build_paper`)

Subagente do LILO (`agents/paper/agent.py`, classe `PaperAgent`,
`name = "paper"`) que **redige manuscritos científicos**: estrutura (outline
IMRaD), seções redigidas com **referências reais**, e *build* da fonte Markdown
para DOCX/TEX/PDF. Porta a skill `build_paper` (originalmente do Claude) para
dentro do LILO. É um `BaseAgent` — roda no orquestrador ou no pipeline Villa
Lobos, **não** é um app standalone.

> Anti-invenção: as referências vêm de fontes reais (`shared/research_sources.py`
> → OpenAlex/PubMed/Europe PMC/CrossRef). O modelo **não pode fabricá-las** — se
> nenhuma é recuperada, a seção sinaliza a lacuna em vez de inventar.

## Escritor (modelo forte, sem GPU local)

- `LILO_PAPER_MODEL` — default **`gpt-oss:120b-cloud`** (Ollama Cloud, **não usa
  a GPU local**). Para 100% local/offline: `llama3.1:8b-instruct-q8_0`
  (qualidade inferior).
- Skill portada (scripts de build, template, perfis): `lilo_skills/skills/build_paper`.

## Tools expostas (`get_tools`)

| Tool | Função | Params |
|------|--------|--------|
| `paper_outline` | Estrutura IMRaD (escopo + metas de profundidade por seção). | `query`*, `journal` |
| `paper_section` | Redige **uma** seção com refs reais (cite `[n]`). | `query`*, `section`*, `journal` |
| `paper_references` | Busca **referências reais** (PubMed/OpenAlex/Europe PMC/CrossRef). | `query`*, `k` (8) |
| `paper_draft` | Rascunho completo: outline + seções IMRaD encadeadas + refs. | `query`*, `journal` |
| `paper_build` | *Builda* DOCX/TEX/PDF da fonte Markdown (pandoc + tectonic). | `root`* |

`section` ∈ `abstract`, `introducao`, `metodos`, `resultados`, `discussao`,
`conclusao`. `journal` é opcional e **calibra o estilo**: o agente busca
artigos recentes do periódico (OpenAlex/CrossRef) como dica de calibre.

## Comportamento (`run`)

O `mode` do contexto seleciona a operação (`draft` é o default):

1. **`references`** — agrega refs reais e formata `[n] autores. título (ano). url`.
2. **`outline`** — escreve a estrutura IMRaD (com `journal_hint` se houver).
3. **`section`** — redige a seção pedida usando **só** as refs recuperadas.
4. **`draft`** — outline + abstract/introdução/métodos/resultados/discussão
   encadeados + bloco de referências.
5. **`build`** — chama `assets/build.sh <root>` da skill (timeout 600s) e
   devolve stdout/stderr do pandoc+tectonic.

## Características de roteamento

- `cost_tier = "ollama"`, `local_only = False` (usa cloud por padrão),
  `latency_class = "slow"` (escrita longa + I/O de refs).
- `KEYWORDS` (build_paper, escrever paper, redigir manuscrito, introdução,
  métodos, resultados, discussão, abstract…) alimentam o roteamento para o
  domínio `paper`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("paper_draft",
                       {"query": "Efeito de X em Y (dados em anexo)",
                        "journal": "Parasitology Research"}))
```

Via MCP: `paper_draft`, `paper_section`, `paper_references` (perfis
`claude_code`, `bio`, `opus`, `pycharm_assistant` — V14.5). Ver também a skill
`build_paper` em `lilo_skills/`.
