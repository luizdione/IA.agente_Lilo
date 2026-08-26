# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.1.0 | **branch:** arch-v12 | **commit:** 78d23c4 Merge PR #10: v13.1.0 — streaming + memória persistente + MCP como tool
- **Testes:** 67 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-26
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.1.0 — 2026-08-26 (streaming + memória persistente + MCP como tool)
- v13.0.0 — 2026-08-25 (LANÇAMENTO: validado na máquina do dono)
- v13.0.2 — 2026-08-25 (modelo default: qwen3 + smoke auto-descoberta)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL) — roadmap de versionamento

- [ ] **v13.2 (qualidade)**: sumarizacao de janela por LLM (substitui a poda
      quando estourar); busca SEMANTICA na memoria (embeddings /api/embed +
      fallback LIKE, padrao herdado do kv legado); teste VIVO da tool mcp
      com um servidor real configurado.
- [ ] **v13.3 (ergonomia)**: tool `esquecer` + comando `\memoria` no REPL;
      sessoes nomeadas (`lilo -c <id>` + `\sessoes`); cores no preview de
      confirmacao (diff verde/vermelho).
- [ ] **v13.4 (ecossistema — so com caso de uso na mao)**: LILO como
      SERVIDOR MCP (expor as tools ao Claude Desktop); provider cloud
      plugavel opcional; cientificos (Scholar/PDF) como tools.
- [ ] Maquina do dono (nao urgente): `pip install -e .` (comando global
      `lilo`) e `python scripts\limpar_mcp_claude.py`.
- [ ] Reavaliar qwen2.5-coder como LILO_MODEL_FAST se o template de tools
      for corrigido em Ollama futuro (hoje: familia qwen3).

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
- **Versionamento**: minor = PR verde em `arch-v12` + CHANGELOG + smoke na
  maquina do dono; patch = fix pontual; feature entra SEMPRE pela regra
  anti-inchaco. Tags sao bloqueadas pelo proxy git — marcos viram branch.

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\check.py             # saude do codigo
python -m lilo                      # o agente (REPL; `lilo -c` retoma)
python scripts\memoria_projeto.py   # atualiza esta memoria
```
