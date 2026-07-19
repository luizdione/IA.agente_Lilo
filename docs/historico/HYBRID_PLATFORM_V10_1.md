# Plataforma Híbrida LILO V10.1 — API + Agente

**Data:** 2026-05-30 (continuação da tarefa `ia_lilo`)
**Escopo:** Proposta de evolução para plataforma híbrida onde o mesmo agente LILO atende simultaneamente Claude Desktop (stdio MCP), Claude Code, OpenClaw, PyCharm e clientes HTTP customizados.

---

## 1. Estado atual (snapshot V10)

Já implementado e funcional:

- `lilo_mcp.py` — servidor MCP/stdio (998 linhas) com 7 perfis curados (`desktop`, `pycharm`, `bio`, `opus`, `claude_code`, `http`, `cowork`).
- `lilo_api.py` — FastAPI/HTTP equivalente (961 linhas) com 20 endpoints expondo as MESMAS tools, paridade total com MCP via `handle_tool_call`.
- `lilo.py` — orquestrador central com 7 subagentes carregados sob demanda; rota por keyword + LLM router + capabilities.
- `agents/villa_lobos/agent.py` — pipeline 5-stage (Orchestrator→Planner→Reader→Worker→Reporter) com smart routing, delegação a especialistas, cache LRU, retry adaptativo, circuit breaker e (V10.1) timings por stage no relatório de retorno.
- `shared/server_profile.py` — política unificada via `config/profiles.yaml` (hot-reload), governa `prefer_local`, `allow_cloud`, `max_iterations` por perfil.

## 2. Lacunas identificadas

| Gap | Impacto | Severidade |
|---|---|---|
| API HTTP e MCP/stdio rodam como processos separados, sem coordenação | Cliente HTTP que abre 1 conexão por request paga warm-up do Ollama sempre | M |
| Não há "single binary" que escolha automaticamente stdio vs HTTP | Onboarding em nova máquina exige editar 2 JSONs | M |
| Falta gateway SSE/WebSocket unificado para clientes web | Streamlit hoje fala HTTP direto; React/mobile seriam relegados a polling | M |
| Ausência de daemon/serviço de SO (systemd / Windows Service) | Após reboot o usuário precisa rodar `.bat` manual | B |
| Telemetria de custo não exposta em endpoint Prometheus/OpenTelemetry | Difícil observar pipeline em produção | B |
| Não existe API key rotacionável por cliente (só 1 token global) | Compartilhar acesso é tudo-ou-nada | M |
| `start` automático do Ollama keep-alive não está no lifecycle do API | Primeira requisição após boot leva ~30s | M |

## 3. Arquitetura proposta — V10.1

```
                          ┌──────────────────────────────────────────┐
   Claude Desktop ───┐    │  lilo_serve.py  (NOVO — daemon raiz)     │
   Claude Code      ─┤    │   ─ supervisor: spawn/health/restart      │
   OpenClaw         ─┼──▶ │   ─ chooses transport per client          │
   PyCharm          ─┤    │   ─ shared singleton: agents, cache, KV   │
   Cowork (sched)   ─┤    │   ─ shared lifecycle: Ollama keep-alive   │
   HTTP/SSE/WS      ─┘    │   ─ shared telemetry: cost_tracker        │
                          └──────────────────────────────────────────┘
                                  │           │           │
                          ┌───────▼──┐  ┌─────▼──────┐  ┌─▼────────────┐
                          │ stdio    │  │ HTTP/SSE   │  │ ws (futuro)  │
                          │ adapter  │  │ adapter    │  │ adapter      │
                          │ (MCP)    │  │ (FastAPI)  │  │              │
                          └──────────┘  └────────────┘  └──────────────┘
                                  │           │
                                  └─────┬─────┘
                                        ▼
                          ┌──────────────────────────┐
                          │  lilo.handle_tool_call    │  (já existente)
                          │  → 7 subagentes           │
                          │  → cost_tracker, kv, etc  │
                          └──────────────────────────┘
```

### 3.1 Componente novo: `lilo_serve.py` (esqueleto já existe)

`lilo_serve.py` (atualmente 86 linhas) precisa evoluir para um **daemon supervisor** que:

1. Sobe `lilo_api.py` (uvicorn) em background.
2. Mantém o `MCP/stdio` disponível através de um wrapper `--transport=stdio`.
3. Faz pré-aquecimento (`ollama keep-alive`) no boot.
4. Expõe `/v1/admin/restart` e `/v1/admin/transports` para troubleshooting.
5. Roda como serviço de SO via NSSM (Windows) ou systemd (Linux).

### 3.2 Componente novo: adapter unificado

Tanto `lilo_mcp.py` quanto `lilo_api.py` hoje **importam** `lilo.handle_tool_call` — então a fonte da verdade já é única. O esforço é apenas wrap-em-um-único-processo:

```python
# lilo_serve.py (esboço V10.1)
import asyncio, uvicorn
from lilo_api import app
from lilo_mcp import mcp

async def run_http():
    config = uvicorn.Config(app, host="0.0.0.0", port=8088, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def run_stdio():
    # mcp.run() é bloqueante; rodar em thread
    await asyncio.to_thread(mcp.run)

async def main():
    await asyncio.gather(run_http(), run_stdio())

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 Lifecycle compartilhado

Tanto MCP quanto HTTP hoje chamam `lilo._load_agents()` lazy — cada um carrega o seu. No daemon supervisor, o `_agents: dict` global do módulo `lilo.py` já é singleton por processo: basta hospedar os dois adapters no MESMO processo Python. Ganho mensurável: warm-up do Ollama (`OLLAMA_KEEP_ALIVE=2h`) compartilhado, cache LRU do Villa compartilhado, KVMemory compartilhada.

### 3.4 Telemetria unificada

`shared/cost_tracker.py` já existe. Para a plataforma híbrida, expor:

- `GET /v1/metrics` em formato **Prometheus** (counter por backend, histogram de latência por stage).
- Endpoint `/v1/admin/cost_recent?since=...` para o dashboard.
- Tag `transport=stdio|http|sse` no log de cada request para distinguir o canal.

### 3.5 Auth multi-cliente

Hoje `LILO_API_TOKEN` é uma string global. Propor:

- `config/api_keys.yaml` com lista `{name, key_hash, scopes[]}`.
- Scopes: `read`, `write`, `admin`, `cost`, `memory`.
- Cliente Claude Desktop (stdio) ignora — confiança implícita.
- Cliente HTTP envia `Authorization: Bearer <key>`; o token é hash-compared.

## 4. Roteiro de implementação (4 sprints curtos)

| Sprint | Entrega | Esforço | Ganho |
|---|---|---|---|
| S1 | `lilo_serve.py` v2 com `--transports=http,stdio`, gather() em asyncio | 2h | Singleton de agentes + 1 binary |
| S2 | `/v1/metrics` Prometheus + tag `transport` em telemetria | 3h | Observabilidade em prod |
| S3 | `config/api_keys.yaml` com hash+scopes | 3h | Compartilhamento granular |
| S4 | NSSM/systemd unit + script `START_LILO_DAEMON.bat` | 2h | Auto-start no boot |

Esforço total: **~10h**. Sem mudanças em `lilo.py`, em `agents/`, ou nos JSONs MCP existentes — backward compatible.

## 5. Riscos & mitigações

| Risco | Mitigação |
|---|---|
| `mcp.run()` é bloqueante e pode travar o loop asyncio | Rodar em `asyncio.to_thread`; expor `/v1/admin/transports` para verificar |
| Conflito de porta 8088 com outras apps locais | `--port` configurável via env; default mantém 8088 |
| `LILO_API_TOKEN` global quebra clientes existentes ao migrar para keys.yaml | Manter fallback: se `keys.yaml` ausente, validar contra `LILO_API_TOKEN` |
| Daemon morto sem ninguém perceber | Health-check externo (`scheduled-tasks ia_lilo_healthcheck` a cada 30min) |

## 6. Próximo passo concreto

Implementar S1 (`lilo_serve.py` v2) na próxima janela. As linhas que mudam:

- `lilo_serve.py`: passar de "fininho wrapper de uvicorn" para "supervisor asyncio gather".
- `START_LILO_WINDOWS.bat`: trocar `python lilo_api.py` por `python lilo_serve.py --transports=http,stdio`.

Sem isso, cada cliente continuará pagando seu próprio warm-up de Ollama e carregando seus próprios agentes — desperdício de RAM e latência em primeiro request.
