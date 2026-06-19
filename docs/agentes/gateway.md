# GatewayAgent — Chat geral e fallback de LLM

Subagente do LILO (`agents/gateway/agent.py`, classe `GatewayAgent`,
`name = "gateway"`) — o **gateway central de LLMs** e o **fallback** do
orquestrador: quando nenhum subagente especializado casa com a query, o Gateway
responde. Roteia para o backend mais adequado (Ollama local → LiteLLM proxy →
Claude API) via `shared/llm_client.py`.

## Tools expostas (`get_tools`)

| Tool | Função | Params |
|------|--------|--------|
| `lilo_chat` | Chat geral / fallback para qualquer pergunta não roteada. | `query`*, `mode` ∈ `chat`/`code`/`bioinfo`/`sql` (def chat), `model` (opcional) |
| `lilo_health` | Status de todos os backends LLM (Ollama, LiteLLM, Anthropic). | — |
| `lilo_models` | Lista os modelos disponíveis no backend ativo. | — |

> O `mode` ajusta o system prompt (código, bioinfo, SQL ou chat). `model`
> permite forçar um modelo específico; senão o `llm_client` resolve pelo tier.

## Comportamento (`run`)

Resolve `mode`/`model` do contexto e chama o `llm_client`, que aplica a cadeia
de backends (Ollama → LiteLLM → Anthropic) conforme a **Policy Engine** (budget
diário, `prefer_local`/`allow_cloud` do perfil). É o ponto onde a política do
servidor pode optar pela nuvem.

## Características de roteamento

- `cost_tier = "ollama"`, `local_only = True` (por padrão), `latency_class = "fast"`.
- **Sem `KEYWORDS`** — é o destino *fallback* quando o roteamento semântico
  (Villa Lobos) não encontra um especialista melhor.

## Uso

```python
from lilo import handle_tool_call
print(handle_tool_call("lilo_chat", {"query": "resuma a teoria endossimbiótica"}))
print(handle_tool_call("lilo_chat", {"query": "escreva um for em Python", "mode": "code"}))
print(handle_tool_call("lilo_health", {}))
```

Via MCP: `lilo_chat`, `lilo_health`, `lilo_models` (perfis que incluem chat;
note que `claude_code`/`claude_desktop` omitem `lilo_chat` pois o cliente já tem
seu próprio chat).
