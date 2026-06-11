---
name: villa_pipeline
description: "Executar pipeline multi-agente Villa Lobos completo para tarefas complexas. Use para tarefas que precisam de planejamento, leitura de contexto, execução e relatório. Triggers: 'villa pipeline', 'pipeline completo', 'planejar e executar', 'tarefa complexa', 'multi-etapas', 'orquestrar agentes', 'plan and execute', 'villa lobos', 'projeto completo'."
---

# Villa Lobos — Pipeline Multi-Agente Completo

## Função
Executa o pipeline completo de 5 estágios do `agents/villa_lobos/agent.py`:
`Orchestrator → Planner → Reader → Worker → Reporter`

Ideal para tarefas complexas que exigem: análise de contexto, planejamento estruturado, leitura de arquivos, execução técnica e relatório final.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py villa "<descricao_da_tarefa>"
```

Com contexto adicional:
```bash
python -c "
import sys; sys.path.insert(0, '.')
from agents.villa_lobos.agent import VillaLobosAgent
agent = VillaLobosAgent()
result = agent.run('<query>', context={
    'base_path': 'C:/Users/luizd/OneDrive/Data_Science/Projetos/IA.agente',
    'iterations': 1,
    'use_reader': True
})
print(result)
"
```

## Estágios do pipeline

| Estágio | Modelo | Função |
|---------|--------|--------|
| Orchestrator | llama3.1:8b | Analisa complexidade, define domínio |
| Planner | phi3:14b | Cria plano detalhado de execução |
| Reader | qwen2.5-coder:14b | Lê arquivos e contexto relevante |
| Worker | qwen2.5-coder:14b | Executa a tarefa técnica |
| Reporter | llama3.1:8b | Gera relatório final estruturado |

## Casos de uso ideais
- Análise de pipeline bioinformático completo
- Refatoração de código com contexto extenso
- Criação de scripts de análise a partir de requisitos
- Revisão e melhoria de métodos experimentais
- Geração de relatórios técnicos a partir de dados

## Passos
1. Receba a descrição completa da tarefa do usuário.
2. Se houver arquivos relevantes, liste-os para o agente via contexto.
3. Execute o pipeline e acompanhe os estágios.
4. Apresente o relatório final do Reporter.
5. Ofereça refinamentos baseados no output.

## Nota
Pipeline executa 100% local via Ollama. Requer Ollama rodando (`ollama serve`).
Para tarefa simples/rápida, use `/villa_quick_ask` no lugar.
