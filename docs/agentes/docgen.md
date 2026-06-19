# DocGenAgent — Geração de documentos de escritório

Subagente do LILO (`agents/docgen/agent.py`, classe `DocGenAgent`,
`name = "docgen"`) que **gera arquivos de escritório** a partir de conteúdo,
dados ou tema: relatórios Word (`.docx`), planilhas Excel (`.xlsx`) e
apresentações (`.pptx`). É um `BaseAgent` — roda no orquestrador ou no pipeline
Villa Lobos.

> Divisão de trabalho: o **LLM gera o CONTEÚDO**; as bibliotecas montam o arquivo
> de forma **determinística** (pandoc, openpyxl, python-pptx). Não substitui o
> subagente **paper** (manuscritos científicos) — `docgen` é para o dia a dia.

## Configuração

- `LILO_DOCGEN_MODEL` — escritor do modo `report`; default **`gpt-oss:120b-cloud`**
  (não usa GPU local).
- `LILO_DOCGEN_OUT` — pasta de saída; default `data/docgen/`.
- Dependências: **pandoc** (docx), **openpyxl** (xlsx), **python-pptx** (pptx).

## Tools expostas (`get_tools`)

| Tool | Função | Params |
|------|--------|--------|
| `make_report_docx` | LLM redige um relatório (Markdown) sobre o tema → `.docx`. | `query`*, `name`, `data` |
| `make_docx` | Converte Markdown já pronto → `.docx`. | `content`*, `name` |
| `make_xlsx` | CSV/TSV/caminho → planilha formatada (header negrito, autofilter, larguras). | `csv` \| `tsv` \| `csv_path`, `name` |
| `make_pptx` | Outline Markdown (`#` título, `-` bullets) → slides. | `outline`*, `name` |

> No perfil MCP `claude_code` ficam expostas `make_report_docx`, `make_xlsx` e
> `make_pptx` (V14.5). `make_docx` está disponível pelo orquestrador/CLI.

## Comportamento (`run`)

O `mode` do contexto seleciona o formato (`report` é o default):

1. **`report`** — o LLM redige um relatório técnico em Markdown (PT-BR, sem
   inventar dados; usa `data` se fornecido) → pandoc → `.docx`.
2. **`docx`** — `content` (Markdown) → pandoc → `.docx`.
3. **`xlsx`** — linhas de `csv_path`/`csv`/`tsv` (autodetecta delimitador) →
   openpyxl (cabeçalho em negrito, `auto_filter`, largura de coluna ≤60).
4. **`pptx`** — cada `#` vira um slide-título; linhas `-`/`*`/`•` viram bullets
   (python-pptx, layout "Title and Content").

O nome do arquivo é sanitizado (alfanumérico + ` _-`, ≤60 chars).

## Características de roteamento

- `cost_tier = "ollama"`, `local_only = False` (modo `report` usa cloud),
  `latency_class = "fast"`.
- `KEYWORDS` (gerar documento, relatório word, docx, planilha, xlsx, excel,
  apresentação, slides, pptx, powerpoint…) roteiam para o domínio `docgen`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("make_xlsx",
                       {"csv": "gene,fold\nTNF,2.1\nIL6,3.4", "name": "deg"}))
print(handle_tool_call("make_report_docx",
                       {"query": "Resumo dos resultados de qPCR", "data": "..."}))
```
