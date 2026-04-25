# LILO — Glossário de Termos de IA

## Modelos e Arquiteturas

| Termo | Descrição |
|-------|-----------|
| **LLM** | Large Language Model — modelo de linguagem com bilhões de parâmetros treinado em texto. Ex: GPT-4, Claude, Llama |
| **SLM** | Small Language Model — modelo menor (1-7B params), roda local. Ex: Phi-3, Qwen2.5-coder:7b |
| **Transformer** | Arquitetura neural base dos LLMs, usa mecanismo de atenção para processar sequências |
| **Token** | Unidade de texto processada pelo modelo (~4 chars em inglês, ~3 em português) |
| **Context Window** | Quantidade máxima de tokens que o modelo processa de uma vez (ex: 128K tokens) |
| **Embedding** | Representação numérica (vetor) de texto, usada para busca semântica |
| **Fine-tuning** | Ajuste de um modelo pré-treinado com dados específicos do domínio |
| **Quantização** | Compressão de modelo (ex: Q4_K_M = 4 bits) para rodar em hardware menor |

## Conceitos de Agentes de IA

| Termo | Descrição |
|-------|-----------|
| **Agente** | Sistema de IA que age autonomamente: percebe, decide e executa ações |
| **Orquestrador** | Componente central que roteia tarefas entre múltiplos agentes (LILO = orquestrador) |
| **Pipeline** | Sequência de agentes executados em ordem. Villa Lobos: Orch → Plan → Read → Work → Report |
| **Tool Use** | Capacidade do LLM de chamar funções/APIs externas durante uma conversa |
| **RAG** | Retrieval-Augmented Generation — busca documentos relevantes antes de gerar resposta |
| **Subagente** | Agente especializado coordenado pelo orquestrador (SQL, PDF, Scholar, Gateway) |
| **Fallback** | Mecanismo de contingência quando o agente principal falha → tenta outro |
| **Chain of Thought** | Técnica onde o modelo "pensa em voz alta" antes de responder |

## Protocolos e Integração

| Termo | Descrição |
|-------|-----------|
| **MCP** | Model Context Protocol — protocolo aberto da Anthropic para conectar LLMs a ferramentas externas. Usa JSON-RPC 2.0 sobre stdin/stdout ou HTTP |
| **FastMCP** | Biblioteca Python que simplifica criação de MCP servers (usada no PyCharm) |
| **JSON-RPC** | Protocolo de chamada remota usando JSON. MCP usa versão 2.0 |
| **stdio** | Standard Input/Output — transporte MCP onde o LLM se comunica via stdin/stdout do processo |
| **StreamableHTTP** | Transporte MCP via HTTP com suporte a streaming de respostas |
| **API Key** | Chave secreta para autenticar chamadas a APIs (Anthropic, OpenAI, etc.) |
| **REST API** | Interface HTTP para comunicação entre serviços (FastAPI no backend LILO) |

## Infraestrutura LILO

| Termo | Descrição |
|-------|-----------|
| **Ollama** | Runtime para rodar LLMs localmente com GPU. Gerencia download e execução de modelos |
| **ChromaDB** | Banco de dados vetorial open-source para armazenar embeddings e fazer busca semântica |
| **Streamlit** | Framework Python para criar dashboards web rapidamente (dashboard LILO) |
| **FastAPI** | Framework Python para APIs HTTP de alta performance (backend LILO) |
| **Docker Compose** | Ferramenta para definir e rodar múltiplos containers Docker simultaneamente |
| **Obsidian** | App de notas em Markdown com links bidirecionais. LILO salva execuções como notas |
| **Policy Engine** | Motor de decisão do LILO que escolhe qual modelo usar baseado em custo/complexidade |

## Tiers de Execução (Policy Engine)

| Tier | Modelo | Custo | Quando Usar |
|------|--------|-------|-------------|
| `NO_LLM` | Nenhum | $0 | Tarefas diretas (listar, status, SQL puro) |
| `OLLAMA_FAST` | qwen2.5-coder:7b | $0 | Perguntas triviais, chat simples |
| `OLLAMA` | llama3.1:8b | $0 | Tarefas simples a médias |
| `OLLAMA_HEAVY` | qwen2.5-coder:14b | $0 | Análise profunda, code review |
| `CLAUDE_SONNET` | claude-sonnet-4 | ~$0.006/1K | Tarefas complexas (ANOVA, ML) |
| `CLAUDE_OPUS` | claude-opus-4 | ~$0.045/1K | Tarefas críticas (revisão sistemática) |

## Bioinformática (termos reconhecidos pelo Policy Engine)

| Termo | Descrição |
|-------|-----------|
| **BLAST** | Basic Local Alignment Search Tool — busca sequências similares em bancos genômicos |
| **Docking** | Simulação computacional de ligação proteína-ligante |
| **PCA** | Principal Component Analysis — redução de dimensionalidade |
| **ANOVA** | Analysis of Variance — teste estatístico para comparar médias de 3+ grupos |
| **t-test** | Teste estatístico para comparar médias de 2 grupos |
| **Phylogenética** | Estudo de relações evolutivas entre organismos via árvores filogenéticas |
| **Transcriptômica** | Estudo do conjunto completo de transcritos (RNA) de uma célula/tecido |
| **Proteômica** | Estudo do conjunto completo de proteínas expressas |

## Siglas Comuns

| Sigla | Significado |
|-------|-------------|
| **AI/IA** | Artificial Intelligence / Inteligência Artificial |
| **ML** | Machine Learning — aprendizado de máquina |
| **DL** | Deep Learning — aprendizado profundo (redes neurais) |
| **NLP** | Natural Language Processing — processamento de linguagem natural |
| **GPU** | Graphics Processing Unit — aceleradora usada para treino/inferência de modelos |
| **CUDA** | Compute Unified Device Architecture — plataforma NVIDIA para computação em GPU |
| **VRAM** | Video RAM — memória da GPU (RTX 3060 = 12GB) |
| **API** | Application Programming Interface |
| **SDK** | Software Development Kit |
| **CLI** | Command Line Interface |
