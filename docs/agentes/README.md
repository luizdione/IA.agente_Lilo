# Subagentes do LILO — índice

Os 10 subagentes vivem em `agents/` (cada um é um `BaseAgent` com
`run`/`get_tools`/`health`/`capabilities`). Registro e roteamento em `lilo.py`
(`_AGENT_REGISTRY`, `_KEYWORD_MAP`, `get_tool_map()`); exposição MCP em
`lilo_mcp.py` + `config/profiles.yaml`.

| Subagente | `name` | Doc dedicada | Principais tools |
|-----------|--------|--------------|------------------|
| ScholarAgent | `scholar` | [scholaragent.md](scholaragent.md) | `scholar_search`, `scholar_synthesize`, `scholar_review` |
| PaperAgent | `paper` | [paper.md](paper.md) | `paper_outline/section/references/draft/build` |
| DocGenAgent | `docgen` | [docgen.md](docgen.md) | `make_report_docx`, `make_docx`, `make_xlsx`, `make_pptx` |
| SkillSmithAgent | `skillsmith` | [skillsmith.md](skillsmith.md) | `propose_agent`, `create_agent_scaffold` |
| PrismAgent | `prism` | [prism_ai.md](prism_ai.md) | `prism_analyze`, `prism_classify`, `prism_audit`, `prism_eda` |
| Villa Lobos | `villa` | [villa_lobos.md](villa_lobos.md) | `villa_pipeline`, `villa_quick_ask`, `villa_explain_routing`, `villa_route` |
| SQLAgent | `sql` | [Analise_SQL.md](Analise_SQL.md) | `sql_query`, `sql_stats` |
| PDFAgent | `pdf` | [pdf.md](pdf.md) | `pdf_summarize`, `pdf_search`, `pdf_list` |
| GatewayAgent | `gateway` | [gateway.md](gateway.md) | `lilo_chat`, `lilo_health`, `lilo_models` |
| DesktopAgent | `desktop` | [desktop.md](desktop.md) | `fs_*`, `run_shell`, `run_python` |

> Todos os 10 subagentes têm página dedicada (tools/params/modos/env/exemplos).
> Padrão de doc: ver [scholaragent.md](scholaragent.md). Arquitetura do pipeline
> e roteamento: `docs/tecnico/`.
