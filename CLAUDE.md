# CLAUDE.md — LILO v13

Guia enxuto para o Claude trabalhar neste repositório. Mantenha curto — entra
no contexto de toda sessão.

## O que é
LILO v13 — agente de terminal **100% local** sobre **Ollama** (estilo Claude
Code): um loop agêntico com tool-calling nativo que lê/escreve/edita arquivos e
roda shell atrás de um portão de permissões. **Sem nuvem no núcleo.** Branch de
desenvolvimento: `arch-v12`. Legado v12.x inteiro: branch `v12.15-legado`
(`git show v12.15-legado:<caminho>` recupera qualquer arquivo).

## Como rodar
```cmd
python -m lilo "tarefa"             # one-shot (REPL: sem argumento)
python scripts\check.py             # saude (sintaxe + pyflakes + pytest)
python scripts\memoria_projeto.py   # atualiza CONTEXT.md (skill /gerente_memoria)
```

**Retomando?** Leia `CONTEXT.md` (raiz) antes de explorar.

## Arquitetura (alvo ~2k linhas)
`lilo/`: `cliente.py` (Ollama /api/chat + tools, num_ctx explícito) ·
`agente.py` (o loop) · `tools.py` (6 tools + `executar_tool` = **choke-point
único**) · `portao.py` (plan/ask/accept_edits/auto, grants escopados) ·
`contexto.py` (LILO.md/CLAUDE.md/CONTEXT.md do cwd como bloco DADOS) ·
`sessoes.py` (SQLite WAL em `%LOCALAPPDATA%\LILO`) · `cli.py` (REPL).

## Regras (as lições do legado — não negociáveis)
- **Anti-inchaço:** funcionalidade nova = TOOL atrás do loop e do choke-point.
  Nunca novo entry point/serviço/dashboard/subagente. Um binário: `lilo`.
- **Só `executar_tool` executa** — implementações de tool são privadas; nenhum
  caminho de execução fora do portão.
- **Sem replay:** aprovação de permissão continua a MESMA conversa.
- **Quem decide executa** (nada de "decide-mas-não-obedece").
- **Idioma:** PT-BR. **Testes:** herméticos (FakeOllama), `pytest` na raiz.
- DBs sempre fora do repo/OneDrive (`%LOCALAPPDATA%\LILO`).
