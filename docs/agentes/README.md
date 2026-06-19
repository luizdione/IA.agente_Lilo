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
| PrismAgent | `prism` | — (ver `agents/prism_ai/`) | `prism_analyze`, `prism_classify`, `prism_audit`, `prism_eda` |
| Villa Lobos | `villa` | — (ver `docs/tecnico/`) | `villa_pipeline`, `villa_quick_ask`, `villa_explain_routing`, `villa_route` |
| SQLAgent | `sql` | — (ver `agents/sql/`) | `sql_query`, `sql_stats` |
| PDFs_library | `pdf` | — (ver `agents/pdf/`) | `pdf_summarize`, `pdf_search`, `pdf_list` |
| GatewayAgent | `gateway` | — (ver `agents/gateway/`) | `lilo_chat`, `lilo_models` |
| DesktopAgent | `desktop` | — (ver `agents/desktop/`) | `fs_*`, `run_shell`, `run_python` |

> As docs dedicadas detalham tools/params/modos/env. Os subagentes sem página
> própria estão cobertos pelo `README.md` da raiz (tabela de subagentes) e pelo
> próprio código. Padrão de doc: ver [scholaragent.md](scholaragent.md).
