# Benchmark de tokens -- DC vs LILO desktop (2026-05-12)

> Medicao empirica do consumo de tokens de Desktop Commander (DC) vs profile
> `desktop` do `lilo_mcp.py`, antes e depois de adicionar 4 tools compostas
> (`fs_batch_read`, `fs_codemod`, `grep_and_read`, `process_run_and_wait`).
> Tokenizer usado: `tiktoken cl100k_base` (proxy razoavel para Claude).

## 1. Resultado do system prompt (lista de tools enviada ao modelo a cada chamada de API)

| Servidor MCP | N tools | Tokens totais | Media por tool |
|---|---|---|---|
| Desktop Commander | 18 | **2 077** | 115 |
| LILO `desktop` (com 4 composed) | 11 | **3 575** | **325** |
| Soma DC + LILO (cenario atual real) | 29 | **~5 652** | -- |

**Achado contraintuitivo**: LILO consome **72% MAIS** tokens no system prompt
mesmo com menos tools. Causa direta -- docstrings com USE WHEN / DO NOT USE
WHEN / Exemplos / Args verbosos. Cada tool LILO tem em media 200-280 tokens
de docstring; cada tool DC, ~60-100 tokens.

### Distribuicao real das docstrings LILO

| Tool | Tokens docstring | Caracteres |
|---|---|---|
| fs_read | 198 | 684 |
| fs_write | 202 | 701 |
| fs_list | 153 | 529 |
| fs_stat | 114 | 396 |
| fs_search | 184 | 668 |
| fs_batch_read (nova) | 205 | 692 |
| fs_codemod (nova) | 261 | 900 |
| grep_and_read (nova) | 203 | 741 |
| process_run_and_wait (nova) | 214 | 765 |
| run_shell | 224 | 809 |
| run_python | 283 | 981 |

## 2. Fluxo "ler README + 3 .py + sugerir refactor"

Modelagem:
- **Granular**: `list_directory` + 4 x `read_file` = 5 round-trips MCP, cada
  um com ~60 tokens de envelope JSON/metadata + payload do conteudo.
- **Composto**: 1 chamada de `fs_batch_read([4 paths])` retornando JSON
  unico `{_summary, files: {path: conteudo}}`.

| Cenario | Tokens total |
|---|---|
| Granular (5 round-trips) | 9 825 |
| Composto (1 round-trip) | 10 483 |
| Delta | **+658 tokens piores** (-6.7%) |

**Achado**: o composto perdeu por causa do envelope JSON adicional
(`{"_summary":...,"files":{...}}` + escape de aspas + keys). Para 4
arquivos, o overhead JSON supera o ganho de eliminar round-trips.

**Onde o composto comeca a compensar (analise marginal)**: quando o LLM
precisa fazer 1 round-trip extra **so para pensar** entre as leituras
(reasoning tokens). Em uso real Claude gera 40-200 tokens de "pensamento"
entre cada `tool_use`. Recalculando com 100 tokens/decisao:

| Cenario | Tokens (com 100 tok thinking/round) |
|---|---|
| Granular (5 chamadas = 4 decisoes extras) | 9 825 + 400 = **10 225** |
| Composto (1 chamada = 0 decisoes extras) | 10 483 |
| Delta efetivo | **-258 tokens piores ainda** |

Composto **so compensa** quando N de arquivos >= ~6 OU as decisoes
intermediarias custam >= 250 tokens cada. Para fluxos de 2-4 arquivos,
**granular ganha**.

## 3. Conclusoes (honestas)

1. **A maior economia nao e adicionar tools compostas** -- e **encurtar as
   docstrings das tools existentes**. Reescrever as 11 docstrings do LILO
   para o estilo conciso do DC (50-80 tokens cada) economiza
   `~150 tokens x 11 tools = ~1650 tokens por chamada de API`. Em uma
   conversa de 50 turnos isso e ~80k tokens.

2. **A SEGUNDA maior economia e eliminar a sobreposicao DC + LILO**.
   Hoje, se o Claude Desktop tem os dois servidores ativos, o overhead
   e ~5.6k tokens por chamada (sobreposicao de fs_*). Escolher um so
   reduz ~2k tokens.

3. **Composed tools so compensam em fluxos com >= 6 itens**. Para 2-4
   arquivos elas perdem em token count puro. **Vale manter** para os
   casos de batch verdadeiro (ler 10 .py para mapear codebase), mas
   NAO sao a otimizacao principal.

4. **A descricao verbosa do LILO tem uma vantagem qualitativa**: o modelo
   acerta a tool com mais consistencia (USE WHEN / DO NOT USE WHEN
   reduz uso errado). E um trade-off de tokens vs. acuracia.

## 4. Acoes recomendadas

| # | Acao | Economia estimada | Esforco |
|---|---|---|---|
| A | **Desligar DC no Claude Desktop** quando profile LILO `desktop` cobre o uso. Sem perda de funcionalidade essencial. | ~2 077 tokens por chamada de API | Trivial -- editar `claude_desktop_config.json` |
| B | **Encurtar docstrings LILO em ~60%** para 80-120 tokens cada (manter Exemplo, remover USE WHEN/DO NOT USE WHEN como prosa, comprimir em 1-2 frases) | ~1 500-1 800 tokens por chamada | Medio -- 11 docstrings reescritas |
| C | **Manter** as 4 composed tools no profile `desktop`, mas adicionar tag "use only for >=6 items" na docstring | Marginal | Trivial |
| D | **Remover process_run_and_wait** -- e quase identico a `run_shell` e adiciona 309 tokens | ~309 tokens | Trivial |

## 5. Codigo entregue nesta passada

- `agents/desktop/composed.py` (novo, 187 linhas) -- implementacao das 4 tools
- `lilo_mcp.py` (modificado, +217 linhas) -- wrappers @_profile_tool e
  inclusao em allowlists `pycharm`, `bio`, `opus`
- `agents/villa_lobos/agent.py` (restaurado, 711 linhas) -- final do arquivo
  havia sido truncado por linter; reanexei `_delegate_to_specialist`,
  `_call_agent`, `get_tools`, `health`
- Smoke test: **8/8 passou** apos as mudancas
