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

## Modelos por subagente LILO

| Subagente | Modelo padrão | Alternativa |
|-----------|--------------|-------------|
| LILO Chat / Orchestrator | llama3.1:8b-instruct-q8_0 | llama3.2:3b |
| Planner (Villa) | phi3:14b-medium-128k | mistral:7b |
| Worker / Code | qwen2.5-coder:14b | codellama:13b |
| SQL / Code | codellama | qwen2.5-coder:7b |
| Scholar / Bio | llama3.1:8b | biomistral |

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

## Requisitos de VRAM (estimativa)

| Modelo | VRAM mín. | Uso típico |
|--------|-----------|------------|
| llama3.2:3b (q4) | 2 GB | Chat rápido |
| llama3.1:8b (q8) | 8 GB | Chat geral |
| qwen2.5-coder:14b | 12 GB | Código |
| phi3:14b (q4) | 8 GB | Planejamento |
| mistral:7b | 5 GB | Fallback geral |

## Trocar modelo de um subagente

Editar `shared/llm_client.py`:
```python
MODELS = {
    "chat": "llama3.1:8b-instruct-q8_0",   # ← alterar aqui
    "code": "qwen2.5-coder:14b",
    "plan": "phi3:14b-medium-128k-instruct-q4_K_M",
}
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
