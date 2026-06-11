# Otimizacao tokens MCP -- antes/depois (2026-05-12 v2)

> Implementacao das otimizacoes A (config) + B (encurtar docstrings) sobre
> o profile `desktop` do `lilo_mcp.py`. Smoke test: **13/13 passou** pos-
> otimizacao.

## 1. Resultado direto

| Servidor MCP | N tools | Tokens system prompt | vs DC |
|---|---|---|---|
| Desktop Commander (referencia) | 18 | **2 077** | -- |
| LILO `desktop` ANTES da otimizacao | 11 | 3 575 | **+72%** |
| **LILO `desktop` DEPOIS da otimizacao** | **10** | **1 670** | **-20%** |

**Economia total no profile desktop**: `3 575 -> 1 670 = -1 905 tokens (-53%)`
**LILO agora e mais barato que DC** com 1 tool a menos.

## 2. O que mudou

### 2.1 Docstrings encurtadas (otimizacao B)

| Tool | Antes (tok) | Depois (tok) | Reducao |
|---|---|---|---|
| fs_read | 198 | ~50 | -75% |
| fs_write | 202 | ~55 | -73% |
| fs_list | 153 | ~50 | -67% |
| fs_stat | 114 | ~25 | -78% |
| fs_search | 184 | ~50 | -73% |
| fs_batch_read | 205 | ~50 | -76% |
| fs_codemod | 261 | ~70 | -73% |
| grep_and_read | 203 | ~55 | -73% |
| run_shell | 224 | ~60 | -73% |
| run_python | 283 | ~50 | -82% |

Padrao adotado: 1 frase de proposito + bloco `Args:` (FastMCP usa `Args:`
para gerar o JSON Schema do parametro). Removido `USE WHEN` / `DO NOT USE
WHEN` em prosa -- isso era a maior fonte de gordura. Exemplos ficaram so
nos casos onde a sintaxe nao e obvia (`fs_search`).

### 2.2 Tool removida

`process_run_and_wait` removido -- redundante com `run_shell` (diferia
apenas no tamanho do buffer stdout). Economia adicional: 309 tokens.

### 2.3 Config Claude Desktop e script de cleanup (otimizacao A)

- `config/mcp/claude_desktop.json` atualizado com metadados explicitos
  sobre a otimizacao e instrucoes para desligar DC.
- Novo: `scripts/disable_desktop_commander.py` -- detecta automaticamente
  qualquer entrada `desktop-commander` no `%APPDATA%\Claude\claude_desktop_config.json`,
  faz backup `.bak` e remove. Suporta `--check` (so lista) e `--restore`
  (volta do backup).

Uso:
```cmd
python scripts\disable_desktop_commander.py --check
python scripts\disable_desktop_commander.py
# Reinicie o Claude Desktop pela bandeja para invalidar o cache de tools.
```

## 3. Impacto cumulativo (Cenario real: Claude Desktop com DC + LILO ativos)

```
Cenario atual (provavel):    Cenario otimizado (A + B):
  DC:           2 077         DC:                0  (desligado via script)
  LILO desktop: 3 575         LILO opus:    ~2 400  (curado, mais util)
  -------                     -------
  TOTAL:        5 652         TOTAL:        ~2 400
```

**Economia por chamada de API**: `~3 252 tokens (-58%)`
**Numa conversa de 50 turnos**: economia de ~163 000 tokens

## 4. Fluxo refactor (`README + 3 .py`)

| Cenario | Tokens | Delta |
|---|---|---|
| Granular (5 round-trips) | 9 776 | baseline |
| Composto (1 round-trip via fs_batch_read) | 10 426 | +650 (-6.6%) |

**Composto continua perdendo para 2-4 arquivos.** Mantido por valer a pena
quando N >= 6 ou quando o reasoning intermediario do modelo passa de ~250
tokens/decisao -- e principalmente porque o ganho do system prompt (item 1)
ja paga o overhead em quase qualquer fluxo.

## 5. Smoke test pos-otimizacao

```
PASSOU: 13 | FALHOU: 0
OK -- todas as verificacoes passaram.
```

## 6. Arquivos modificados nesta passada

- `lilo_mcp.py` -- 10 docstrings encurtadas, `process_run_and_wait` removido
- `config/mcp/claude_desktop.json` -- metadados de otimizacao + instrucoes
- `scripts/disable_desktop_commander.py` (NOVO, 110 linhas)

## 7. Recomendacao final

Rodar **uma unica vez** no Windows:
```cmd
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python scripts\disable_desktop_commander.py
# Fechar Claude Desktop pela bandeja (icone perto do relogio)
# Reabrir
```

Resultado esperado: cada chamada de API ao Claude Opus passa a ter ~2 400
tokens de tools no system prompt em vez dos ~5 652 atuais.
