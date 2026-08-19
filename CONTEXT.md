# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de
> sessoes do LILO e do Claude Code).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v12.14.0 | **branch:** claude/open-agent-studio-analysis-wgru64 | **commit:** fe35a3e feat(v12.13): dashboard minimalista — layout Claude completo (V18.9)
- **Testes:** 137 funcoes de teste (rode `python scripts/check.py`)
- **Diagnostico:** P0=0 | P1=1 | P2=1 | INFO=2 | OK=12
- **Atualizado em:** 2026-08-19
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v12.14 — 2026-08-19 (V18.10: gerente de memória do projeto)
- v12.13 — 2026-08-19 (V18.9: dashboard minimalista — layout Claude completo)
- v12.12 — 2026-08-09 (V18.8: E8 — redesign visual do dashboard, estilo Claude)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [ ] Commitar `agents/paper/` **da maquina Windows do dono** (unico P1 do
      diagnostico; resolve tambem o P2 da env `LILO_PAPER_MODEL`).
- [ ] Smoke visual do dashboard v12.13 na maquina do dono
      (`streamlit run dashboard.py`) — redesign foi validado so por
      sintaxe/testes; ajustes finos de layout a pedido.
- [ ] Revisar e mergear o PR #5 (serie v12.5→v12.13, CI verde, draft).
- [ ] E5b (roadmap): scrubber de segredos antes de envio cloud.

## Decisoes-chave (MANUAL)

- Local-first: Ollama resolve; nuvem so com `LILO_ALLOW_CLOUD` + budget
  diario (`LILO_DAILY_BUDGET`) + gate `cloud_send` (E5).
- Streamlit mantido; UI React/editor REJEITADA (ver
  `docs/tecnico/analise_open_agent_studio.md`, secao rejeitados).
- KV SQLite e o storage primario de memoria; markdown e interface (E4).
- Roadmap Open Agent Studio: H1 (QW1-7) e H2 (E1-E8) COMPLETOS; H3
  (S1-S5) opcional, avaliar com caso de uso na mao.
- Layout do dashboard espelha o Claude: sidebar enxuta com expanders,
  composer-cartao (anexos/pastas/mic/modelo/modo), tema claro/escuro.
- Novo provedor LLM = via LiteLLM YAML (S2), nunca client hardcoded.

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\check.py                          # saude do codigo
python scripts\diagnostico_lilo.py --fast        # auditoria compacta
python scripts\memoria_projeto.py                # atualiza esta memoria
streamlit run dashboard.py                        # UI -> localhost:8100
```
