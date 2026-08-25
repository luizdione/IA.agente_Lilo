# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.1.0 | **branch:** arch-v12 | **commit:** db6a72e feat: scripts/limpar_mcp_claude.py — remove MCP legado do Claude Desktop (backup + idempotente)
- **Testes:** 67 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-25
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.1.0 — 2026-08-26 (streaming + memória persistente + MCP como tool)
- v13.0.0 — 2026-08-25 (LANÇAMENTO: validado na máquina do dono)
- v13.0.2 — 2026-08-25 (modelo default: qwen3 + smoke auto-descoberta)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [x] v13.0 LANCADO E VALIDADO NA MAQUINA DO DONO (25/08): smoke PASSOU na
      RTX 3060 com qwen3:14b (aceite canonico: leu o erro e consertou
      sozinho); icone LILO na Area de Trabalho; pasta legada local apagada.
      Repo local do dono: C:\github\LILO.
- [x] v13.1 ENTREGUE (26/08): streaming no terminal, tools memorizar/lembrar
      (validadas ao vivo entre processos) e tool mcp (allow-list LILO_MCP,
      dep opcional). 67 testes.
- [ ] Backlog v13.2: sumarizacao de janela por LLM; embeddings na memoria
      (busca semantica) quando houver caso de uso; teste vivo de MCP.
- [ ] Se o template do qwen2.5-coder for corrigido em Ollama futuro,
      reavaliar como LILO_MODEL_FAST (hoje: familia qwen3).

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
