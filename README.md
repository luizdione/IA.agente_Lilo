# LILO v14 — assistente local de pesquisa (Ollama + Open WebUI + ponte MCP)

![Status](https://img.shields.io/badge/status-ativo-brightgreen)
![Version](https://img.shields.io/badge/version-14.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-yellow)
![GPU](https://img.shields.io/badge/GPU-RTX%203060%2012GB-76b900)

**LILO** (Local Intelligent LLM Orchestrator) é o assistente de pesquisa do autor
(bioinformática e ciência de dados), **100% local**: um modelo de chat residente na
RTX 3060, uma interface de chat pronta (Open WebUI em container) e uma **ponte MCP no
host** que dá ao modelo as ferramentas do dono — biblioteca de PDFs, estatística,
Python/R/WSL, memória dos projetos, skills do Claude, repositórios git e literatura
(PubMed e afins). O diálogo é sempre em português.

A v14 nasceu de um critério único, medido: **"2+2" tem de responder na hora**
(1º token em menos de 1 s). Tudo o que entra passa por `lilo.ps1 bench`.
A geração anterior (v13, agente de terminal) está no branch `marco/v13.12-terminal`;
o legado v12 em `v12.15-legado`.

## Arquitetura (três peças, nenhuma reinventada)

| Peça | O que é | Onde |
|---|---|---|
| **Motor** | Ollama 0.35+ com o modelo derivado `lilo` (`ollama/Modelfile.lilo`: qwen3:14b Q4_K_M, contexto 8192, SYSTEM em PT). Candidata a base forte: `lilo-30b` (qwen3:30b-a3b-instruct-2507, híbrido GPU+CPU), que só entra no seletor se passar no bench. | host, GPU |
| **Interface** | Open WebUI em Docker Compose (`compose.yaml`), `127.0.0.1:3000`, sem login. Seletor enxuto (D-0022): só cinco presets, **LILO**, **LILO Pesquisa**, **LILO Desktop**, **LILO Orquestrador (Claude)** e **LILO Pesquisa (Claude)**; os modelos crus ficam fora pela whitelist do `compose.yaml` e a base `claude-sonnet-5-5` (API da Anthropic, chave no `.env`) por um registro inativo. Atalhos `/pasta` (abre o seletor de pasta), `/pasta_colada`, `/repo`, `/skill` e um `/<skill>` por skill do dono. | container |
| **Ponte `lilo-host`** | Pacote `lilo_host/` (FastMCP, streamable HTTP) em `127.0.0.1:8790` com 3 grupos: `conhecimento` (14 tools), `analise` (10), `exec` (5, token obrigatório) e o proxy `/literatura/mcp` para o Docker MCP Gateway (`paper-search`, só busca). | host, conda `datascience` |
| **Plugins do Claude** | MCPs remotos do plugin bio-research que aceitam conexão sem login, ligados direto na interface: PubMed, bioRxiv, ChEMBL, ensaios clínicos e Open Targets (só no preset Pesquisa (Claude): seus schemas somam 4 k tokens e são buscados a cada mensagem, o que custa 3,7 s de 1º token no modelo local). **Desktop Commander** (o mesmo do Claude) no host atrás do `mcpo`, só loopback, com token: `lilo.ps1 desktop up`. | container / host |

Regras de velocidade que o código obedece: um só modelo de chat, chamado **sem opções
de runner** (opção diferente = recarga); `think:false` por padrão; nada roda escondido
na GPU; a GPU é do dono — o interruptor `~/.ollama_delegate/switch.json` em `off`
impede qualquer carga (`lilo.ps1 gpu-livre` / `gpu-ok`).

## Como rodar

```powershell
.\lilo.ps1 up          # ponte + gateway de literatura + interface + aquecimento + presets
.\lilo.ps1 status      # interruptor, modelos na GPU, interface, ponte, gateway, último bench
.\lilo.ps1 bench       # portão: TTFT p95 < 1 s e >= 25 tok/s (alvos: --alvo ollama|webui)
.\lilo.ps1 down
```

Outros comandos: `abrir` (navegador) · `warm` · `convivencia` (lilo + embeddings na GPU) ·
`presets` · `inicio` (atalho de inicialização do Windows) · `ponte [up|down]` ·
`gateway [up|down]` · `desktop [up|down]` (Desktop Commander via mcpo) · `smoke` (tools de
cada grupo) · `indexar [status|falhas]` (biblioteca de PDFs, incremental) · `gpu-livre [motivo]` ·
`gpu-ok`.

### Controles da caixa de mensagem (como no Claude)

- **Seletor de modelo** (botão "LILO ▾" à direita da caixa): os cinco presets, nada mais. Qual
  usar: tabela "Qual LILO usar", abaixo.
- **Botão "Integrações"** (ícone ao lado do "+"): cinco interruptores do LILO, cada um com engrenagem:
  - **Escolha Automática de Parâmetros** (engrenagem → nível): `baixo` (rápido, sem pensar, 512 tokens),
    `medio` (padrão), `alto` (pensa), `extra`, `maximo` (pensa e revisa), `ultracode` (código em etapas
    com testes). É a "profundidade de raciocínio"; ajusta temperature, top_p, num_predict e `think`
    (ou `reasoning_effort` no Claude) de uma vez, sem tocar em `num_ctx`.
  - **Pensar fundo**: atalho para o nível `alto` nesta conversa.
  - **Modo de agir** (engrenagem → modo): `automatico` (tools do preset), `manual` (só leitura; pede
    confirmação antes de alterar), `aceitar_edicoes` (lê e edita arquivos; sem shell, processo ou git),
    `plano` (nenhuma tool) e `ignorar_permissoes` (tudo, sem perguntar). Os modos restringem de verdade
    as tools enviadas ao modelo; fronteira honesta: a Open WebUI não tem diálogo de aprovação por
    chamada, então "manual" = restrição + instrução.
  - **Plano**: atalho para o modo `plano`.
  - **Pasta de trabalho** (engrenagem → caminho): o LILO trabalha nessa pasta; vazio = ele abre o
    seletor de pasta do Windows (`pasta_escolher`). `/pasta` na caixa faz o mesmo; `/pasta_colada`
    usa o caminho copiado no Explorer.
- **Painel "Controles"** (ícone no canto superior direito): "Parâmetros Avançados" continua sendo a
  escolha manual, parâmetro a parâmetro.
- **Grupos de trabalho** na barra lateral: "Pastas" → "+" cria uma pasta; arraste o chat para dentro;
  no "..." da pasta, "Editar" dá prompt do sistema e conhecimento ao grupo. Há uma pasta de exemplo.

**O LILO age por padrão** (memória, biblioteca, pastas, estatística, Python, R, WSL, git e skills);
sem ferramentas o modelo só pode dizer que "não consegue acessar arquivos". Use o "Modo de agir"
para restringir. Regra dos presets: **conteúdo da internet nunca fica no mesmo preset que executa
código** (Pesquisa/Pesquisa-Claude não executam; os demais não têm web). Presets com muitas tools
só sobre o Claude (contexto 200k); no `lilo` (8k) cada preset fica abaixo de ~30 tools locais,
porque os schemas entram no prompt (o Ollama reaproveita o cache a partir da 2ª mensagem; medido:
Pesquisa 18 tools = 1º token 0,37 s, 28 tools locais = 0,53 s).

### Qual LILO usar

| Tarefa | Preset |
|---|---|
| Rodar ou depurar script Python/R, estatística, gráfico, ler planilha ou PDF, git, skills | **LILO** |
| Buscar artigos, conferir uma referência, qualquer coisa que precise de internet | **LILO Pesquisa** |
| Revisão de literatura séria: PubMed, bioRxiv, ChEMBL, ensaios clínicos, Open Targets | **LILO Pesquisa (Claude)** |
| Projeto em várias etapas, "faça a análise inteira", pipeline de ponta a ponta | **LILO Orquestrador (Claude)** |
| Arquivos e processos do Windows fora das pastas de projeto (`lilo.ps1 desktop up` antes) | **LILO Desktop** |

O "LILO que pensa e distribui" é o Orquestrador (Claude): planeja, divide em etapas e executa cada
uma com as ferramentas locais. Nenhum preset delega a outro modelo (a ponte não tem tool de
delegação). Os controles valem em todos: **Pensar fundo** para problema difícil, **Plano** para só
planejar, **Modo de agir** como freio.

Requisitos: Windows 11, Docker Desktop, Ollama, conda `datascience` (Python 3.11 com
`mcp`, `httpx`, `sentence-transformers`, `chromadb`, `pingouin`, `pymupdf`, `psutil`,
`pyyaml`, `mcpo`), R e WSL para as tools de execução. Segredos e caminhos locais ficam no
`.env` (nunca versionado; modelo em `.env.example`).

Antivírus que inspeciona HTTPS (Kaspersky): o `up` exporta a raiz dele do Windows para
`%LOCALAPPDATA%\LILO\ca-bundle.pem`, montado no container como `SSL_CERT_FILE`; sem isso a
Claude falha com `CERTIFICATE_VERIFY_FAILED` de dentro do container.

## Ferramentas da ponte

- **conhecimento** — memória dos projetos (`.project-memory/`), `ler_pdf`, `ler_texto`,
  `resumir_arquivo`, `biblioteca_buscar`/`biblioteca_status` (1.121 PDFs: bge-m3 + Chroma +
  FTS5 com fusão RRF, índice em `E:\data\lilo\biblioteca`), `skills_listar`/`skill_ler`
  (848 skills do Claude lidas no lugar, sem cópia), `pasta_listar`/`pasta_buscar`,
  `repos_listar` (repositórios de `C:\GitHub`).
- **analise** — `estat_*` (pingouin/statsmodels, conferidos contra o R), `bio_parse_log`,
  `docx_ler`/`docx_escrever`.
- **exec** — `executar_python`, `executar_r`, `executar_wsl`, `executar_git` (só em
  `C:\GitHub`, deny-list de comandos destrutivos), `skill_rodar`. Exige Bearer token,
  timeout e pasta própria (`E:\data\lilo\trabalho`); conteúdo da internet nunca fica
  no mesmo preset que executa código.
- **literatura** — `search_pubmed`, `search_europepmc`, `search_biorxiv`,
  `search_crossref`, `search_semantic` (Docker MCP Gateway, catálogo mínimo gerado por
  `scripts/gateway_catalogo.py`).

O Claude Code também usa os grupos `conhecimento` e `analise` por HTTP
(`scripts/conectar_claude_code.ps1`).

## Portões medidos (RTX 3060, GPU quieta)

| Portão | Resultado |
|---|---|
| G0 Ollama | TTFT p95 0,07 s · 33 tok/s |
| G1 convivência | lilo + bge-m3 + jina 100 % na GPU · "2+2" < 0,1 s |
| G2 interface | TTFT p95 0,11 s · 32 tok/s · 1 chamada por mensagem |
| G3 ponte | 55 testes · interface executou Python, R e WSL |
| G4 biblioteca | item conhecido no top-5: 97 % (EN) / 83 % (PT) · busca p95 0,56 s |
| G5 literatura | 5 tools · 1ª busca PubMed 3,9 s · seguintes 1,1 s |

Bake-off (`scripts/bakeoff_tools.py` + `bench.py` + `avaliar_biblioteca.py --idioma pt`):
qwen3:14b tem o 1º token 3× mais rápido e escolha de tool 16/16; gemma4:12b gera 40–55 %
mais rápido. A base continua qwen3:14b; `lilo-gemma` fica no Ollama, fora do seletor (D-0022).

Bases híbridas (12/10, GPU quieta; `bench --sem-portao`, `bakeoff_tools --caminho ollama`,
`bakeoff_codigo`): os três não cabem inteiros nos 12 GB e rodam parte na CPU.

| Modelo | 1º token p95 | tok/s | tools (8 pedidos) | código (3 tarefas) |
|---|---|---|---|---|
| `lilo` qwen3:14b, 9 GB | 0,094 s | 33,8 | 8/8 | 3/3 em 5,5 s |
| `lilo-30b` qwen3:30b-a3b, 18 GB | 0,317 s | 26,9 | 8/8 (15,6 s por chamada) | 0/3 com `think:false` (ver nota) |
| `lilo-32b` qwen2.5:32b, 20 GB | 2,68 s | 2,7 | 8/8 (49,6 s) | 3/3 em 35 s |
| `lilo-oss` gpt-oss:20b, 14 GB | 3,61 s | 43,2 | 8/8 (28,3 s) | 3/3 em 12,9 s |

Nota: a tag `qwen3:30b-a3b` do Ollama é a variante **pensante**: com `think:false` ela vaza o
raciocínio como texto em inglês antes da resposta (por isso o 0/3 no código, que é o extrator
achando prosa); com o raciocínio ligado ("Pensar fundo") a resposta sai limpa, mas "2+2" leva
9 s e um código 60 s. Para uma base 30B rápida e sem raciocínio a tag certa é
`qwen3:30b-a3b-instruct-2507-q4_K_M` (baixada em 12/10; `Modelfile.lilo-30b` já aponta para ela e
o `lilo-30b` só vira o preset "LILO Forte" se passar no bench). O `lilo-32b` é inviável nesta placa
(2,7 tok/s) e o `gpt-oss:20b` sempre raciocina (ignora `think:false`; aceita `low`/`medium`/`high`,
que a Escolha Automática de Parâmetros já manda). O padrão continua o `lilo`. Desde 12/10 (D-0022)
nenhum híbrido aparece no seletor: continuam no Ollama só para medição.

## Estrutura

```
lilo.ps1            operação (up/down/status/bench/...), Windows PowerShell 5.1
compose.yaml        Open WebUI (lista de modelos, conexões MCP, presets via API)
ollama/             Modelfile.lilo (o seletor), Modelfile.lilo-gemma|30b|32b|oss (bases fora dele)
lilo_host/          ponte MCP: servidor.py (3 grupos + proxy), biblioteca, estatistica,
                    execucao, skills, pastas, projetos, resumir, docx, bioparsers, comum
scripts/            bench.py · owui_presets.py · lilo_host_serve.py · mcp_smoke.py ·
                    indexar_biblioteca.py · avaliar_biblioteca.py · bakeoff_tools.py ·
                    gateway_catalogo.py · convivencia.py · criar_atalho.py
tests/              test_host_*.py (ponte, sem GPU)
lilo/               núcleo da v13 (agente de terminal) — a retirar na F5
```

Memória viva do projeto (fora do repo): `OneDrive\...\Projetos\IA.agente\.project-memory\`.
