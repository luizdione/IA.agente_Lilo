---
name: lilo_chat
description: "Ativar o LILO como assistente de chat geral com LiteLLM/Ollama. Use quando o usuario quer conversar com LILO, perguntar algo geral, usar modo bioinfo, code ou sql via gateway local. Triggers: 'lilo chat', 'fala com lilo', 'gateway', 'llama', 'ollama chat', 'lilo responde', 'pergunte ao lilo'."
---

# LILO Chat — Gateway LLM Local

## Função
Roteia a conversa para o gateway LLM do LILO (LiteLLM proxy + Ollama local).

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py "{{query}}"
```

Modos disponíveis via gateway:
- `chat` — conversa geral (gemma3:12b)
- `code` — programação (qwen2.5-coder:14b)
- `bioinfo` — bioinformática e biologia molecular (gemma3:12b)
- `sql` — queries e banco de dados (qwen2.5-coder:14b)

## Passos
1. Identifique o modo adequado pela natureza da pergunta.
2. Execute via bash com `python lilo.py "<query>"` na raiz do projeto.
3. Se o gateway não estiver disponível, informe o usuário para executar `.\lilo.ps1` ou `start.bat`.
4. Apresente a resposta do agente diretamente.

## Fallback
Se LiteLLM estiver offline, o agente faz fallback automático para Ollama direto (`http://localhost:11434`).

## Nota
O usuário é PhD em Biologia Molecular e Cientista de Dados. Sempre use terminologia técnica precisa. Responda em português brasileiro.
