---
name: lilo_models
description: "Listar, gerenciar e trocar modelos LLM do LILO (Ollama + LiteLLM). Use para ver modelos disponíveis, baixar novos modelos, trocar modelo de um subagente, ver consumo de VRAM. Triggers: 'listar modelos', 'lilo models', 'modelos ollama', 'trocar modelo', 'baixar modelo', 'qual modelo usar', 'vram', 'ollama pull', 'modelos disponiveis', 'mudar llm'."
---

# LILO Models — Gestão de Modelos LLM

## Função
Gerencia os modelos LLM disponíveis no ecossistema LILO (Ollama local + LiteLLM proxy). Lista, baixa, remove e troca modelos por subagente.

## Como executar

```bash
# Listar modelos instalados
ollama list

# Via LiteLLM API
curl http://localhost:4000/models \
  -H "Authorization: Bearer sk-litellm-local-dev"

# Via Python
import sys; sys.path.insert(0, 'C:/Users/luizd/OneDrive/Data_Science/Projetos/IA.agente')
from shared.llm_client import get_client, MODELS
print(MODELS)
```

## Modelos por subagente LILO (fonte: `shared/models.py` / `.env` — 2026-08)

| Papel | Modelo atual | Chave (`.env` / `_DEFAULTS`) |
|-------|--------------|------------------------------|
| Chat / Orchestrator / Reporter | gemma3:12b | `OLLAMA_MODEL` / `chat` |
| Planner (Villa) | qwen3:14b | `OLLAMA_MODEL_PLAN` / `plan` |
| Worker / Reader / Code | qwen2.5-coder:14b | `OLLAMA_MODEL_CODE` / `code` |
| Triagem rápida (autocomplete) | qwen2.5-coder:7b-instruct | `OLLAMA_MODEL_FAST` / `autocomplete` |
| Worker de conhecimento (nuvem) | gpt-oss:120b-cloud | `LILO_CLOUD_MODEL` |
| Embed (RAG / router) | mxbai-embed-large (bge-m3 opcional) | `OLLAMA_MODEL_EMBED` / `embed` |

## Gerenciar modelos

```bash
# Baixar novo modelo
ollama pull <nome_modelo>

# Remover modelo (liberar disco)
ollama rm <nome_modelo>

# Ver detalhes e VRAM estimada
ollama show <nome_modelo>

# Testar modelo específico
ollama run <nome_modelo> "teste rápido"
```

## Requisitos de VRAM (estimativa, RTX 3060 12 GB)

| Modelo | VRAM aprox. | Uso |
|--------|-------------|-----|
| qwen2.5-coder:7b-instruct | ~6 GB | Triagem rápida |
| gemma3:12b | ~9 GB | Chat geral |
| qwen3:14b | ~10 GB | Planejamento |
| qwen2.5-coder:14b | ~10 GB | Código |
| mxbai-embed-large | ~1 GB | Embeddings |
| gpt-oss:120b-cloud | — (Ollama Cloud) | Worker de conhecimento |

## Trocar modelo de um subagente

Fonte única: **`shared/models.py`** (`_DEFAULTS`) ou o `.env` (`OLLAMA_MODEL*`).
Editar `MODELS` em `shared/llm_client.py` é **no-op** — hoje ele só re-exporta de
`shared/models.py`, e os demais consumidores importam de lá.

Pelo `.env` (não precisa editar código):
```
OLLAMA_MODEL=gemma3:12b            # chat
OLLAMA_MODEL_CODE=qwen2.5-coder:14b
OLLAMA_MODEL_PLAN=qwen3:14b
OLLAMA_MODEL_FAST=qwen2.5-coder:7b-instruct
```
Ou em `shared/models.py`:
```python
_DEFAULTS = {"chat": "gemma3:12b", "code": "qwen2.5-coder:14b",
             "plan": "qwen3:14b", "autocomplete": "qwen2.5-coder:7b-instruct"}
```

## Passos
1. Execute `ollama list` para ver modelos instalados.
2. Compare com o mapa de subagentes acima.
3. Se modelos necessários estiverem faltando, execute `ollama pull <modelo>`.
4. Para trocar o modelo de um subagente, edite `shared/llm_client.py`.
5. Reinicie o serviço após alterações: `.\lilo.ps1` ou `start.bat`.
6. Verifique com `/lilo_health` que tudo voltou a funcionar.

## Modelos especializados para biologia
```bash
ollama pull biomistral          # Biologia/medicina
ollama pull medllama3           # Literatura médica
ollama pull nous-hermes2-mixtral # Raciocínio avançado
```
