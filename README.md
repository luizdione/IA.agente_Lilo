# LILO v13 — agente de terminal 100% local

![Status](https://img.shields.io/badge/status-ativo-brightgreen)
![Version](https://img.shields.io/badge/version-13.5.0-blue)
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
  em streaming** no terminal.
- **Um loop agêntico** com tool-calling nativo do Ollama (`/api/chat` + `tools`).
- **Nove tools**: `ler`, `escrever`, `editar`, `listar`, `buscar`, `shell`,
  `memorizar`/`lembrar` (memória persistente entre sessões) e `mcp`
  (servidores MCP externos, allow-list `LILO_MCP`, dep. opcional) — todas
  atrás de um único choke-point com portão de permissões
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
python scripts\check.py       # saúde do código (sintaxe + pyflakes + pytest)
```

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
