---
name: villa_quick_ask
description: "Consulta rápida ao Villa Lobos (Ollama local) sem pipeline completo. Use para perguntas técnicas pontuais que precisam de resposta local/offline, sem passar por todos os 5 estágios. Triggers: 'villa quick', 'pergunta rapida villa', 'ollama responde', 'consulta local', 'resposta offline', 'villa ask', 'quick ask'."
---

# Villa Lobos — Consulta Rápida

## Função
Consulta direta ao modelo Ollama local (llama3.1:8b ou phi3:14b) via Villa Lobos, pulando os estágios Planner/Reader do pipeline completo. Resposta técnica rápida, 100% offline.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python -c "
import sys; sys.path.insert(0, '.')
from agents.villa_lobos.agent import VillaLobosAgent
agent = VillaLobosAgent()
result = agent.run('<pergunta>', context={'iterations': 1, 'use_reader': False})
print(result)
"
```

Ou via CLI LILO com detecção automática:
```bash
python lilo.py "villa <pergunta>"
```

## Modelos disponíveis (Ollama local)
```bash
# Listar modelos instalados
ollama list

# Executar modelo específico direto
ollama run llama3.1:8b-instruct-q8_0 "<pergunta>"
ollama run qwen2.5-coder:14b "<pergunta de código>"
ollama run phi3:14b-medium "<pergunta complexa>"
```

## Diferença vs. villa_pipeline
| | villa_quick_ask | villa_pipeline |
|-|-----------------|----------------|
| Estágios | Worker + Reporter | Todos os 5 |
| Velocidade | Rápido (~30s) | Lento (2-5min) |
| Contexto | Sem leitura de arquivos | Lê arquivos do projeto |
| Ideal para | Perguntas pontuais | Projetos complexos |

## Passos
1. Receba a pergunta técnica do usuário.
2. Execute via Python inline com `use_reader=False`.
3. Apresente a resposta diretamente.
4. Se a tarefa for mais complexa que esperado, sugira `/villa_pipeline`.

## Nota
Requer Ollama rodando localmente (`ollama serve`). Sistema prompts do Villa Lobos são calibrados para PhD em Biologia Molecular/Data Science — terminologia técnica precisa.
