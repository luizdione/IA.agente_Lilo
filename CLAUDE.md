# CLAUDE.md — LILO v14

Guia enxuto para o Claude trabalhar neste repositório. Mantenha curto — entra
no contexto de toda sessão. Memória viva (estado, decisões, tarefas) fica FORA
do repo: `OneDrive\...\Projetos\IA.agente\.project-memory\` (PMM).

## O que é
LILO v14 — assistente local de pesquisa: Ollama na RTX 3060 (modelo derivado `lilo`),
Open WebUI em container (`compose.yaml`) e a ponte MCP `lilo_host/` no host (conda
`datascience`), operados por `lilo.ps1`. Branch de desenvolvimento: `v14-docker`.
v13 (agente de terminal) em `marco/v13.12-terminal`; legado v12 em `v12.15-legado`.

## Como rodar / medir
```powershell
.\lilo.ps1 up | down | status | bench | smoke | presets | indexar | gateway up
C:\Users\luizd\miniforge3\envs\datascience\python.exe -m pytest tests\test_host_*.py -q
ollama create lilo -f ollama\Modelfile.lilo      # depois de editar o Modelfile
```
Python do projeto: `C:\Users\luizd\miniforge3\envs\datascience\python.exe` (nunca o Python do sistema).

## Regras (critério do dono: "2+2" responde na hora)
- **A GPU é do dono.** Antes de carregar QUALQUER modelo, ler `~/.ollama_delegate/switch.json`
  (`lilo.ps1 status`); `off` = não carregar nem religar. Guardas falham FECHADAS.
- **Um modelo de chat (`lilo`), chamado sem opções de runner** (`num_ctx`, `num_gpu`...): opção
  diferente = recarga de 11 s. `think:false` por padrão. Nada roda escondido na GPU.
- **Nada é "pronto" sem `lilo.ps1 bench`** (alvos `ollama` e `webui`), com a GPU quieta: o
  plugin lumen do Claude Code reindexa na GPU por ~55 min a cada sessão e derruba a vazão pela
  metade — conferir `/api/embed` no `%LOCALAPPDATA%\Ollama\server.log` antes de medir.
- **Preferir peça pronta** (Open WebUI, catálogo MCP do Docker) a código próprio. Funcionalidade
  nova entra como tool da ponte, não como serviço/dashboard novo.
- **Segurança:** `exec` só com token; deny-lists de shell e git; conteúdo da internet nunca no
  mesmo preset que executa código. `.env` nunca é impresso, movido ou versionado.
- **`lilo.ps1` roda no Windows PowerShell 5.1:** só ASCII; nunca uma variável `$Switch`.
- **Idioma:** PT-BR, inclusive no SYSTEM do modelo e nos presets. Push e PR são do autor.
- Arquivos com `\` vão pela Write/Edit (o heredoc do Bash colapsa `\\`); validar `.py` com
  `py_compile`; chamar `.ps1` pela ferramenta PowerShell.

## Estrutura
```
lilo.ps1  compose.yaml  ollama/Modelfile.*  lilo_host/  scripts/  tests/test_host_*.py
lilo/  tests/test_v13*.py  scripts/{check,smoke_lilo,servir_mcp,...}   <- v13, a retirar (F5)
```
