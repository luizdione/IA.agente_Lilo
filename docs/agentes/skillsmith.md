# SkillSmithAgent — Criador de subagentes (meta-skill)

Subagente do LILO (`agents/skillsmith/agent.py`, classe `SkillSmithAgent`,
`name = "skillsmith"`) que **cria o scaffold de novos subagentes** do LILO a
partir de uma descrição: gera um `BaseAgent` que **compila**, valida-o, e
devolve as instruções de registro. É uma meta-skill — o LILO ajudando a
estender o próprio LILO.

> **Não auto-modifica o roteamento.** O scaffold é gerado e validado, mas a
> ativação (editar `_AGENT_REGISTRY`, `_KEYWORD_MAP`, `get_tool_map()` em
> `lilo.py`) fica **a cargo do usuário** — por segurança e revisão.

## Configuração

- `LILO_SKILLSMITH_MODEL` — usado só para **inferir metadados** (nome, keywords,
  tools) quando o chamador não os fornece; default **`gpt-oss:120b-cloud`**.
- O scaffold em si é **determinístico** (template Python), sem LLM.

## Tools expostas (`get_tools`)

| Tool | Função | Params |
|------|--------|--------|
| `propose_agent` | O LLM infere specs (nome snake_case, keywords, tools) de uma descrição em linguagem natural. | `query`* (descrição) |
| `create_agent_scaffold` | Cria `agents/<name>/agent.py` (compila) + instruções de registro. | `name`*, `description`*, `keywords`, `tools` |

## Comportamento (`run`)

1. Lê `name`/`description`/`keywords`/`tools` do contexto.
2. Sem `name`: chama o LLM (`_propose`) para inferir os metadados da descrição.
3. Valida o nome (`snake_case`, `[a-z][a-z0-9_]{1,30}`, não-keyword) e recusa se
   já existir `agents/<name>/`.
4. Gera `agents/<name>/agent.py` a partir do template (classe `BaseAgent` com
   `run`/`get_tools`/`KEYWORDS`) e `__init__.py`.
5. **Valida que compila** (`python -m py_compile`); se não compilar, avisa.
6. Devolve a linha pronta para o `_AGENT_REGISTRY` + os próximos passos de
   ativação manual.

## Características de roteamento

- `cost_tier = "ollama"`, `local_only = False` (inferência via cloud),
  `latency_class = "fast"`.
- `KEYWORDS` (criar agente, novo subagente, criar skill, nova skill, scaffold,
  gerar agente, skill creator, criar capacidade) roteiam para `skillsmith`.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("create_agent_scaffold",
                       {"name": "blast_runner",
                        "description": "Roda BLAST local e resume os hits"}))
# -> cria agents/blast_runner/agent.py (compila) + instrucoes de registro
```

Via MCP: `create_agent_scaffold` (perfis `claude_code`, `bio`, `opus`,
`pycharm_assistant` — V14.5).
