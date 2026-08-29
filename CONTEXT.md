# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.10.0 | **branch:** arch-v12 | **commit:** 2ee9ac3 Merge PR #21: docs(memoria) — CONTEXT.md pós-v13.10
- **Testes:** 129 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-29
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.10.0 — 2026-08-28 (o registro MCP à prova de shell)
- v13.9.0 — 2026-08-27 (conserto: a conexão com o Claude Code)
- v13.8.0 — 2026-08-27 (LILO dentro do Claude Code: memória + delegar)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [x] **Ponte Claude Code VALIDADA na maquina do dono (29/08)**: `lilo:
      C:\Users\luizd\miniforge3\python.exe C:\github\LILO\scripts\servir_mcp.py
      - Connected`. Fecha a v13.10 (o comando sem hifens sobreviveu ao
      PowerShell 5.1 real).
- [ ] **Maquina do dono** (o que falta): `python scripts\criar_atalho.py`
      (icone -> lilo web); `pip install PyMuPDF` (tool ler_pdf). Opcional:
      `pip install -e .` (comando `lilo`), `python scripts\limpar_mcp_claude.py`
      (entrada legada no Claude Desktop).
- [ ] Redundancia a decidir com o dono: ele ja tinha um MCP `ollama-local`
      (C:\github\ollama-delegate\server.py) que sobrepoe o `delegar` do
      mcp-serve. Manter os dois ou aposentar o antigo?
- [ ] **v13.11 = friccoes de USO REAL** (terminal, web e Claude Code) que o
      dono relatar -> correcao + teste de regressao. Foi assim nas v13.9/13.10.
- [ ] GATED ate caso de uso nomeado pelo dono: provider cloud plugavel;
      cientificos alem do ler_pdf (Scholar/RAG).
- [ ] Reavaliar qwen2.5-coder como LILO_MODEL_FAST se o Ollama corrigir o
      template de tools (hoje: familia qwen3).
- [x] Arco v13.0->v13.10 fechado e mergeado (PRs #6-#20, CI verde): loop,
      portao, sessoes, memoria semantica, `lilo web`, ler_pdf, mcp-serve +
      `delegar`. Detalhes NAO repetidos aqui — ver docs/versoes/CHANGELOG.md.

## Decisoes-chave (MANUAL)

- **Reset radical (24/08)**: legado v12.x (42k LOC) demolido; recuperavel em
  `git show v12.15-legado:<caminho>`.
- 100% offline: so Ollama; nuvem NAO existe no nucleo.
- **Anti-inchaco**: funcionalidade nova = TOOL atras do loop/choke-point,
  nunca entry point novo. Emenda do dono (26/08): interface web voltou como
  SUBCOMANDO (`lilo web`), nao como servico separado — "um binario" de pe.
- Permissoes: plan/ask/accept_edits/auto, grants escopados, sem replay;
  default `ask`; never-commit-unless-asked. DBs em %LOCALAPPDATA%\LILO.
- **Ponte MCP (licao v13.9+v13.10)**: no `claude mcp add`, `--env` e
  variadico (precisa de outra opcao antes do nome) e o `--` nao sobrevive ao
  PowerShell — por isso o comando registrado NAO pode ter hifens. Travado em
  tests/test_mcp_ponte.py; `scripts/diagnosticar_mcp.py` da a causa exata.
- **Versionamento**: minor = PR verde em `arch-v12` + CHANGELOG + validacao
  viva; tags sao bloqueadas pelo proxy — marcos viram branch.

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\check.py             # saude do codigo
python -m lilo                      # o agente (REPL; `lilo -c` retoma)
python scripts\memoria_projeto.py   # atualiza esta memoria
```
