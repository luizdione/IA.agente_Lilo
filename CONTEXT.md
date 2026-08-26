# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.5.0 | **branch:** arch-v12 | **commit:** 6ec9a0f Merge PR #14: v13.4.0 — LILO como servidor MCP (round-trip validado)
- **Testes:** 92 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-26
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.5.0 — 2026-08-26 (blindagem offline + ergonomia de manutenção)
- v13.4.0 — 2026-08-26 (ecossistema: LILO como SERVIDOR MCP)
- v13.3.0 — 2026-08-26 (ergonomia: esquecer, \memoria, sessões nomeadas, cores)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [x] v13.2/v13.3/v13.4 ENTREGUES (26/08, validadas ao vivo): resumo de
      janela por LLM + memoria semantica; esquecer/\memoria/\sessoes/
      `lilo -c <id>`/cores; `lilo mcp-serve` (LILO como servidor MCP p/
      Claude Desktop) com round-trip cliente<->servidor provado.
- [ ] Maquina do dono (nao urgente): `git pull`; `pip install -e .` (comando
      global `lilo`); `pip install mcp` se for usar mcp/mcp-serve;
      `python scripts\limpar_mcp_claude.py`; reconfigurar o Claude Desktop
      com o mcp-serve novo (snippet no README).
- [ ] GATED ate caso de uso nomeado (decisao): provider cloud plugavel;
      cientificos (Scholar/PDF) como tools.
- [x] v13.5 ENTREGUE (26/08): blindagem offline (*-cloud fora da
      auto-descoberta), icone abre POWERSHELL com o REPL (regravar com
      criar_atalho.py), LILO_DEBUG, \atualizar, \esquecer, \memoria
      exportar/importar.
- [ ] v13.6: coletar friccoes de USO REAL do dono -> correcoes; candidata
      cientifica: tool ler_pdf (PyMuPDF opcional) quando o dono nomear o caso.
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
