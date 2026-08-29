# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.12.0 | **branch:** arch-v12 | **commit:** e1cfb49 Merge PR #23: v13.11.0 — LILO ancorado no ambiente conda registrado
- **Testes:** 139 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-29
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.12.0 — 2026-08-29 (delegar respeita o interruptor de GPU)
- v13.11.0 — 2026-08-29 (o LILO no ambiente conda certo)
- v13.10.0 — 2026-08-28 (o registro MCP à prova de shell)
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
- [ ] **Ambiente do dono**: os pacotes de bioinformatica dele estao em
      `miniforge3\envs\datascience`. Registrar o LILO com o python DESSE env
      (`conectar_claude_code.ps1 -Python ...\envs\datascience\python.exe`)
      + `pip install mcp` la. Sem isso o `shell`/`delegar` quebra em script
      cientifico. (v13.11 ancora o PATH no interpretador registrado.)
- [x] DECIDIDO (29/08): manter os DOIS servidores — papeis distintos.
      `ollama-local` = arbitragem da GPU (status/ligar/desligar com checagem
      de VRAM, + embeddings); `lilo` = trabalho agentico (delegar com loop,
      arquivos, shell, ler_pdf, memoria). So `ollama_delegar` x `delegar` se
      sobrepoem, e o do LILO e mais capaz. v13.12 fecha a lacuna: o delegar
      avisa quando a GPU foi liberada de proposito (LILO_OLLAMA_SWITCH).
- [ ] **v13.13 = proximas friccoes de USO REAL** (terminal, web e Claude
      Code) -> correcao + teste de regressao (padrao das v13.9-v13.12).
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
