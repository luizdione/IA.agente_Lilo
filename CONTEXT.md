# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.0.0 | **branch:** arch-v12 | **commit:** ca6d1ab Merge PR #8: v13.0.2 — default qwen3 + think:false + smoke auto-descoberta (VALIDADO ao vivo)
- **Testes:** 59 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-25
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.0.0 — 2026-08-25 (LANÇAMENTO: validado na máquina do dono)
- v13.0.2 — 2026-08-25 (modelo default: qwen3 + smoke auto-descoberta)
- v13.0 — 2026-08-24 (RENASCIMENTO: agente de terminal 100% local sobre Ollama)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [x] v13.0 LANCADO E VALIDADO NA MAQUINA DO DONO (25/08): smoke PASSOU na
      RTX 3060 com qwen3:14b (aceite canonico: leu o erro e consertou
      sozinho); icone LILO na Area de Trabalho; pasta legada local apagada.
      Repo local do dono: C:\github\LILO.
- [ ] v13.1 (backlog): streaming da resposta, memoria semantica KV como
      tools memorizar/lembrar, sumarizacao de janela por LLM, MCP como tool.
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
