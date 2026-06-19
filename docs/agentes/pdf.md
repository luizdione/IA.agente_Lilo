# PDFAgent (PDFs_library) — Leitura e busca em PDFs científicos

Subagente do LILO (`agents/PDFs_library/agent.py`, classe `PDFAgent`,
`name = "pdf"`) que **lê, sumariza e busca** em PDFs científicos: extrai
introdução, métodos, DOI e metadados de artigos, e faz busca na biblioteca
local. É um `BaseAgent` — roda no orquestrador ou no pipeline Villa Lobos.

> A biblioteca local de PDFs fica em `PDF_DIR` (`.env`, default
> `./PDFs_library/data`).

## Tools expostas (`get_tools`)

| Tool | Função | Params |
|------|--------|--------|
| `pdf_summarize` | Sumariza um artigo em PDF em diferentes modos. | `file_path`*, `mode` ∈ `simple`/`introduction`/`methods`, `query` (pergunta específica, opcional) |
| `pdf_search` | Busca (semântica/textual) na biblioteca local de PDFs. | `query`* |
| `pdf_list` | Lista os PDFs disponíveis na biblioteca. | `filter` (por nome/assunto, opcional) |

## Comportamento (`run`)

Detecta o modo a partir do contexto/query:

- **`simple`** — resumo geral do artigo;
- **`introduction`** / **`methods`** — extrai e resume a seção pedida;
- com `query` — responde uma pergunta específica sobre o artigo;
- **`search`** — varre a biblioteca local; **`list`** — enumera os PDFs.

A extração de texto + sumarização rodam com LLM **local**.

## Características de roteamento

- `cost_tier = "ollama"`, `local_only = True`, `latency_class = "medium"`
  (parsing de PDF + sumarização).
- `KEYWORDS` (pdf, artigo, paper, documento, resumo, sumarizar, introdução,
  métodos, doi, pubmed, abstract, "analise o artigo"…) roteiam para `pdf`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("pdf_summarize",
                       {"file_path": "PDFs_library/data/artigo.pdf", "mode": "methods"}))
print(handle_tool_call("pdf_list", {}))
```

Via MCP: `lilo_pdf` (perfis `claude_code`, `bio`, `opus`, …) e a aba **PDF** do
dashboard. Para **escrever** manuscritos, ver o subagente [paper](paper.md);
para revisão de literatura multi-fonte, [scholaragent](scholaragent.md).
