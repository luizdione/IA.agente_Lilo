# LILO v13 — agente de terminal 100% local

![Status](https://img.shields.io/badge/status-ativo-brightgreen)
![Version](https://img.shields.io/badge/version-13.12.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-yellow)
![Arch](https://img.shields.io/badge/arch-v12-purple)

**LILO** renasceu: um agente de IA no terminal, estilo Claude Code, rodando
**100% offline** sobre **Ollama** (RTX 3060). Ele **gerencia, escreve, conserta
e cria projetos** com acesso real ao computador — arquivos e shell — atrás de
um portão de permissões.

A plataforma anterior (v12.x: dashboard Streamlit, MCP server, API HTTP,
10 subagentes, ~42k linhas) foi **demolida por decisão do dono** — virou uma
colcha de retalhos sem a capacidade central (não havia tool-calling nativo em
lugar nenhum). Tudo está preservado no branch **`v12.15-legado`**:
`git show v12.15-legado:<caminho>` recupera qualquer arquivo.

## O que é o núcleo v13

- **Um binário**: `lilo` (REPL interativo ou `lilo "tarefa"`), com **resposta
  em streaming** no terminal — e **`lilo web`** (v13.7), o MESMO agente num
  chat no navegador (`http://localhost:8100`, só 127.0.0.1): confirmações do
  portão viram botões e a conversa persiste no mesmo SQLite (`lilo -c` retoma
  no terminal o que começou no navegador).
- **Um loop agêntico** com tool-calling nativo do Ollama (`/api/chat` + `tools`).
- **Onze tools**: `ler`, `ler_pdf` (artigos/manuais, dep. opcional PyMuPDF),
  `escrever`, `editar`, `listar`, `buscar`, `shell`,
  `memorizar`/`lembrar`/`esquecer` (memória persistente entre sessões) e
  `mcp` (servidores MCP externos, allow-list `LILO_MCP`, dep. opcional) —
  todas atrás de um único choke-point com portão de permissões
  (modos `plan` / `ask` / `accept_edits` / `auto`; *never-commit-unless-asked*).
- **Memória**: sessões em SQLite (fora do OneDrive, `%LOCALAPPDATA%\LILO`) +
  contexto do projeto lido de `LILO.md`/`CLAUDE.md`/`CONTEXT.md` do diretório.
- **Zero nuvem, zero framework**: dependências de runtime = `requests`
  (+ `python-dotenv`).

## Como rodar

```cmd
pip install -r requirements.txt
copy .env.example .env        # ajuste LILO_ALLOW e o modelo
python -m lilo "sua tarefa"   # one-shot
python -m lilo                # REPL
python -m lilo web            # chat no navegador (localhost:8100)
python scripts\criar_atalho.py  # ícone na área de trabalho → navegador
python scripts\check.py       # saúde do código (sintaxe + pyflakes + pytest)
```

O ícone da área de trabalho abre o `lilo web` (a janela PowerShell que fica
atrás é o servidor). Prefere só terminal? `python scripts\criar_atalho.py
--terminal` regrava o atalho para o REPL.

Requisitos: Python 3.11+, [Ollama](https://ollama.com) ≥ 0.9 com um modelo
com suporte a tools (default: `qwen3:14b` — a família qwen2.5-coder tem o
template de tool-calling quebrado no Ollama 0.32.x; o smoke detecta e avisa).

## LILO no Claude Desktop (servidor MCP, v13.4)

O mesmo binário serve as tools ao Claude Desktop (`pip install mcp` antes):

```jsonc
// %APPDATA%\Claude\claude_desktop_config.json
"mcpServers": {"lilo": {"command": "python",
                        "args": ["-m", "lilo", "mcp-serve"],
                        "cwd": "C:\\github\\LILO"}}
```

Modo do servidor: `LILO_MCP_SERVE_MODE` (default `accept_edits` — leituras e
escrita na allow-list passam; shell pede `auto`; git nunca passa sem grant).

## LILO dentro do Claude Code (v13.8)

Uma linha registra o LILO como servidor MCP do Claude Code em **todos** os
seus projetos (pré-requisito: `pip install mcp`):

```powershell
.\scripts\conectar_claude_code.ps1
# ou, para o LILO viver num ambiente conda especifico (v13.11):
.\scripts\conectar_claude_code.ps1 -Python C:\Users\voce\miniforge3\envs\SEU_ENV\python.exe
```

**Escolha o ambiente com cuidado**: o LILO roda os seus scripts com o
interpretador registrado (e ancora o PATH nele). Se os seus pacotes estão num
env conda, registre o python DELE.

O Claude real passa a ter, em qualquer pasta: **memória persistente
compartilhada** (`memorizar`/`lembrar`/`esquecer` — o mesmo banco do LILO),
**`ler_pdf`** e **`delegar`** — despachar uma tarefa completa ao agente LILO
local (loop + tools + portão sobre a sua GPU): grátis, offline, privado.
Expectativa honesta: o modelo local é bem mais fraco que o Claude — delegue
tarefas simples/privadas/em lote. Desfazer: `claude mcp remove --scope user
lilo`.

Não conectou? `python scripts\diagnosticar_mcp.py` diz a causa exata — ele
faz um handshake JSON-RPC real com o servidor e mostra o que o Claude Code
enxerga (`claude mcp list/get`).

## Claude Code nos seus modelos Ollama (ponte inversa)

O Ollama expõe um endpoint compatível com a API da Anthropic — dá para rodar
o **Claude Code CLI** sobre os seus modelos locais (nada sai da máquina):

```powershell
.\scripts\claude_ollama.ps1            # default qwen3:14b
.\scripts\claude_ollama.ps1 qwen3:4b   # ou outro modelo instalado
```

Expectativa honesta: modelos de 4–14B são muito mais fracos que o Claude —
use para tarefas simples/privadas; o LILO continua sendo o agente nativo.

## Regra anti-inchaço (a lição do legado)

> Funcionalidade nova entra como **TOOL atrás do loop e do choke-point** —
> nunca como novo entry point, serviço, dashboard ou subagente.
> Um binário: `lilo`. Cloud, RAG, Scholar e MCP só voltam como tools (v13.x).

## Estrutura

```
lilo/            pacote do agente (cliente Ollama, loop, tools, portão, sessões, CLI)
scripts/         check.py (saúde) · memoria_projeto.py (CONTEXT.md) · smoke_lilo.py (teste vivo)
tests/           suíte hermética (FakeOllama, sem rede)
docs/versoes/    CHANGELOG.md
```

Estado vivo do projeto: **`CONTEXT.md`** (raiz).
