# LILO — Análise e propostas de novas execuções (2026-06-14)

Run autônomo da scheduled task **desenvolvimento-lilo**. Objetivo: produtividade,
tempo de resposta, integração entre subagentes, integração perfeita com o Claude
(skills do LILO que "resolvem" sem o Claude recorrer a skills externas), redução
de tokens, e dashboard localhost no padrão Claude Desktop.

## O que foi entregue neste run (V14.5)

**Guarda de orçamento de saída do MCP** — economia de tokens num único ponto.
- `shared/mcp_budget.py` + wrapper `_budget_wrap` em `lilo_mcp.py` (cobre todas as
  21 tools sem tocar em cada função; schema MCP preservado).
- `LILO_MCP_MAX_CHARS` (48000 default) e `LILO_MCP_HEAD_RATIO` (0.7). Saída
  pequena = no-op; saída grande = head+tail com marcador legível pelo modelo.
- +9 testes (117 passam). README/CHANGELOG sincronizados (estavam em v10.6 vs
  código real V14.4).

## Diagnóstico

| Eixo | Estado | Gargalo observado |
|---|---|---|
| Tokens | Bom após V14.5 (teto por saída) | Falta cache de resultados idênticos e descrições de tool longas no profile `opus` (carregadas todo turno) |
| Tempo de resposta | Ollama local + worker cloud `gpt-oss:120b` | Sem cache de query→resposta; `lilo_scholar`/`web_fetch` repetem chamadas externas |
| Integração entre agentes | Porta única (Villa Lobos) + cadeia multi-especialista | `Reader` ainda não consulta `kv_memory`/`chat_memory` (item do roadmap A/C) |
| Integração com Claude | 21 tools curadas no profile `opus` | Skills geradas (199) não expostas como tools — Claude às vezes recorre a skills externas |
| Dashboard | Tema Claude Desktop, modos de execução, microfone | Sem painel de tokens economizados; sem "tool inspector" estilo Claude Desktop |

## Propostas priorizadas para os próximos runs

### P1 — Cache de saída de tools (tempo + tokens) — ALTO impacto, baixo risco
Memoizar (TTL curto, ex. 10 min) resultados de tools *idempotentes e caras*:
`lilo_scholar`, `lilo_web_search`, `lilo_web_fetch`, `prism_classify`. Chave =
hash dos args. Reaproveita V14.5 (`shared/mcp_budget`) e o `kv_memory` existente
(ns=`tool_cache`). Reduz latência e chamadas externas repetidas dentro de uma
sessão. Configurável por `LILO_MCP_CACHE_TTL` (0 = off).

### P2 — Descrições de tool em 2 níveis (tokens por turno) — ALTO impacto
As descrições verbosas (`USE WHEN`/`DO NOT USE`/`Exemplo`) entram no contexto a
*cada turno*. Propor descrições curtas por padrão + `lilo_tool_help(name)` que
devolve a versão longa sob demanda. Medir com o juiz LLM se a acurácia de seleção
cai; só aplicar se não cair. Economia estimada: ~1–3k tokens/turno no profile
`opus`.

### P3 — Expor skills geradas como capacidade de primeira classe (autossuficiência)
Hoje as 199 skills só são alcançáveis via `lilo_run_skill`/`lilo_list_skills`.
Criar um índice semântico leve (TF-IDF/embeddings locais) e uma tool
`lilo_solve(task)` que escolhe e executa a skill certa — para o Claude resolver
"localmente" sem recorrer a skills externas (alinha ao objetivo da task).

### P4 — Smart context no Villa-Lobos (Reader → memória) — roadmap A/C
`Reader` (stage 3) deve consultar `kv_memory`+`chat_memory` quando a query
referenciar contexto anterior ("lembra do que falamos sobre X"). Entregar
`shared/memory_facade.py::get_relevant_context()` (já especificado no ROADMAP).

### P5 — Dashboard: painel "Economia & Tools" no padrão Claude Desktop
Aba mostrando tokens economizados pela guarda V14.5 (logar `omitted` por chamada
em `kv_memory` ns=`mcp_budget`), últimas tool calls (estilo "tool inspector" do
Claude Desktop) e custo do dia (`lilo_cost_today`). Visual já segue o tema.

## Métricas a acompanhar
- Tokens médios por tool call (antes/depois da V14.5) — instrumentar `_budget_wrap`.
- Hit rate do cache (P1).
- Acurácia de roteamento (juiz LLM) ao encurtar descrições (P2).

---
*Gerado autonomamente pela scheduled task `desenvolvimento-lilo`. Próximo run
sugerido: implementar P1 (cache de tools).*
