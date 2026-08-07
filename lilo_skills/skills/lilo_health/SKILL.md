---
name: lilo_health
description: "Verificar status de todos os serviços do LILO (Ollama, LiteLLM proxy, modelos disponíveis). Use para diagnóstico, ver se serviços estão online, troubleshooting. Triggers: 'lilo health', 'status dos servicos', 'verificar ollama', 'litellm status', 'servicos online', 'check health', 'diagnostico lilo', 'ollama rodando', 'gateway status'."
---

# LILO Health — Diagnóstico de Serviços

## Função
Verifica o status de todos os serviços do ecossistema LILO:
- **Ollama** — servidor de modelos LLM local
- **LiteLLM Proxy** — gateway unificado de LLMs
- **Modelos** — lista de modelos disponíveis

## Como executar

```bash
# Via CLI LILO (mais completo)
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py health

# Via script de health check direto
python llm-gateway/agents/health_check.py

# Verificação rápida Ollama
curl http://localhost:11434/api/tags

# Verificação LiteLLM
curl http://localhost:4000/health
```

## Serviços verificados

| Serviço | URL | Porta | Status esperado |
|---------|-----|-------|-----------------|
| Ollama | http://localhost:11434 | 11434 | `{"models": [...]}` |
| LiteLLM Proxy | http://localhost:4000 | 4000 | HTTP 200 |
| LiteLLM Models | http://localhost:4000/models | 4000 | lista de modelos |

## Interpretação dos resultados

```json
{
  "ollama": {"status": "ok", "models": ["gemma3:12b", "qwen2.5-coder:14b"]},
  "litellm": {"status": "ok"},
  "litellm_models": {"status": "ok", "models": ["chat", "code"]}
}
```

## Troubleshooting

| Problema | Diagnóstico | Solução |
|----------|------------|---------|
| Ollama offline | `ollama: {status: offline}` | Execute: `ollama serve` |
| LiteLLM offline | `litellm: {status: offline}` | Execute: `.\lilo.ps1` ou `start.bat` |
| Sem modelos | `models: []` | Execute: `ollama pull gemma3:12b` |
| Timeout | Erros de conexão | Verifique firewall/VPN |

## Passos
1. Execute `python lilo.py health`.
2. Apresente o JSON de status formatado.
3. Se algum serviço estiver offline, forneça o comando de inicialização.
4. Se todos OK, confirme quais modelos estão disponíveis para cada subagente.
5. Sugira `ollama pull <modelo>` se modelos necessários estiverem faltando.

## Modelos recomendados
```bash
ollama pull gemma3:12b                    # chat + orchestrator + reporter
ollama pull qwen2.5-coder:14b             # code + worker + reader
ollama pull qwen3:14b                     # planner
ollama pull qwen2.5-coder:7b-instruct     # triagem rápida (autocomplete)
ollama pull mxbai-embed-large             # embeddings (RAG/router)
```
