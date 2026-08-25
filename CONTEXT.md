# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** 13.0.0-dev | **branch:** arch-v12 | reset em andamento (F0 feito)
- **Testes:** rode `python scripts/check.py`
- **Atualizado em:** 2026-08-24
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13 F0 — demolicao do legado + esqueleto do pacote `lilo/` (arch-v12)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [ ] F1: `config.py` + `log.py` + `cliente.py` (Ollama /api/chat multi-turno
      + tools, retry/keep_alive herdados, num_ctx explicito) + testes FakeOllama.
- [ ] F2: `agente.py` (loop) + tools ler/listar/buscar + `contexto.py`.
- [ ] F3: escrever/editar/shell + `portao.py` (pausa-no-ponto, sem replay).
      Aceite canonico: LILO cria script, roda, VE o erro e conserta sozinho.
- [ ] F4: `sessoes.py` (SQLite WAL em %LOCALAPPDATA%) + `lilo -c`.
- [ ] F5: REPL completo, plan e2e, lilo.bat, smoke_lilo.py, CHANGELOG v13.0.

## Decisoes-chave (MANUAL)

- **Reset radical aprovado (24/08)**: legado v12.x (42k LOC) demolido; TUDO
  recuperavel no branch `v12.15-legado`. Plano completo na sessao de 24/08.
- 100% offline: so Ollama; nuvem NAO existe no nucleo (provider pluggavel
  poderia voltar como tool em v13.x).
- CLI unico (`lilo`); sem Streamlit/API/MCP no nucleo.
- **Anti-inchaco**: funcionalidade nova = TOOL atras do loop/choke-point,
  nunca novo entry point. Cientificos (Scholar/PDF/Prism/RAG) = tools futuras.
- Permissoes: plan/ask/accept_edits/auto, grants escopados, sem replay;
  default `ask`; never-commit-unless-asked.
- DBs fora do repo/OneDrive (%LOCALAPPDATA%\LILO).

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\check.py             # saude do codigo
python -m lilo                      # o agente (quando F2+ estiver pronto)
python scripts\memoria_projeto.py   # atualiza esta memoria
```
