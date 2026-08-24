# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de
> sessoes do LILO e do Claude Code).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v12.15.0 | **branch:** claude/open-agent-studio-analysis-wgru64 | **commit:** 71de6a2 fix(v12.15): scrubber le LILO_SCRUB via environ.get inline (nao doc-morta)
- **Testes:** 150 funcoes de teste (rode `python scripts/check.py`)
- **Diagnostico:** P0=0 | P1=1 | P2=1 | INFO=2 | OK=12
- **Atualizado em:** 2026-08-20
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v12.15 — 2026-08-20 (V18.11: guarda de versão do dashboard + scrubber pré-cloud)
- v12.14 — 2026-08-19 (V18.10: gerente de memória do projeto)
- v12.13 — 2026-08-19 (V18.9: dashboard minimalista — layout Claude completo)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [ ] Commitar `agents/paper/` **da maquina Windows do dono** (unico P1 do
      diagnostico; resolve tambem o P2 da env `LILO_PAPER_MODEL`).
- [ ] Smoke visual do dashboard na maquina do dono
      (`streamlit run dashboard.py`). v12.15 tornou o diagnostico self-service:
      se o Streamlit for < 1.39 aparece um `st.error` pedindo upgrade, e o selo
      na sidebar mostra versao do build + do Streamlit. **Se "nao mudou nada":
      1) cheque o selo (esta em v12.15.0?); 2) `streamlit --version` >= 1.39;
      3) rode a partir do repo, nao do OneDrive.** Ajustes finos a pedido.
- [ ] Revisar e mergear o PR #5 (serie v12.5→v12.15, CI verde, draft).
- [x] E5b: scrubber de segredos pre-cloud (`shared/scrubber.py`) — FEITO v12.15.

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
- **Dashboard exige Streamlit >= 1.39** (classes `st-key-*`); abaixo disso o
  layout degrada em silencio. Guard no boot + selo de versao avisam (v12.15).
- Novo provedor LLM = via LiteLLM YAML (S2), nunca client hardcoded.

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\check.py                          # saude do codigo
python scripts\diagnostico_lilo.py --fast        # auditoria compacta
python scripts\memoria_projeto.py                # atualiza esta memoria
streamlit run dashboard.py                        # UI -> localhost:8100
```
