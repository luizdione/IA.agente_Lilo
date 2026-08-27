# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de sessoes).

## Estado atual (AUTO)
<!-- AUTO:estado -->
- **Versao:** v13.8.0 | **branch:** arch-v12 | **commit:** 375b1f6 feat(v13.7): `lilo web` — o chat no navegador de volta, sem repetir o v12
- **Testes:** 117 funcoes de teste (rode `python scripts/check.py`)
- **Atualizado em:** 2026-08-27
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
- v13.8.0 — 2026-08-27 (LILO dentro do Claude Code: memória + delegar)
- v13.7.0 — 2026-08-26 (o chat no NAVEGADOR de volta: `lilo web`)
- v13.6.0 — 2026-08-26 (primeira tool científica: ler_pdf)
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

- [x] v13.2/v13.3/v13.4 ENTREGUES (26/08, validadas ao vivo): resumo de
      janela por LLM + memoria semantica; esquecer/\memoria/\sessoes/
      `lilo -c <id>`/cores; `lilo mcp-serve` (LILO como servidor MCP p/
      Claude Desktop) com round-trip cliente<->servidor provado.
- [ ] Maquina do dono (nao urgente): `git pull`; `pip install -e .` (comando
      global `lilo`); `pip install mcp` se for usar mcp/mcp-serve;
      `pip install PyMuPDF` p/ ler_pdf; `python scripts\criar_atalho.py`
      (icone -> lilo web); `python scripts\limpar_mcp_claude.py`; Claude Desktop
      com o mcp-serve novo (snippet no README); Claude Code sobre Ollama:
      `scripts\claude_ollama.ps1`.
- [ ] GATED ate caso de uso nomeado (decisao): provider cloud plugavel;
      mais cientificos (Scholar/RAG) alem do ler_pdf.
- [x] v13.5 ENTREGUE (26/08): blindagem offline (*-cloud fora da
      auto-descoberta), icone abre POWERSHELL com o REPL (regravar com
      criar_atalho.py), LILO_DEBUG, \atualizar, \esquecer, \memoria
      exportar/importar.
- [x] v13.6 ENTREGUE (26/08): tool ler_pdf (11a; PyMuPDF opcional; paginada,
      corte com dica de continuacao) no choke-point E no mcp-serve; gate
      cientifico aberto pelo dono ("execute o 13.6"). + ponte inversa
      claude_ollama.ps1 (Claude Code rodando nos modelos Ollama locais).
- [x] v13.7 ENTREGUE (26/08): `lilo web` — chat no NAVEGADOR (decisao do
      dono "Web primeiro"): subcomando stdlib em 127.0.0.1:8100, mesmo
      loop/portao, confirmacao por botoes (Event bloqueante), persistencia
      compartilhada com o terminal; icone LILO.lnk -> web (--terminal volta).
- [x] v13.8 ENTREGUE (27/08): LILO dentro do Claude Code — `delegar` no
      mcp-serve (loop inteiro no Ollama local; ancora em CLAUDE_PROJECT_DIR;
      portao do serve vale DENTRO da tarefa) + conectar_claude_code.ps1
      (claude mcp add --scope user, sintaxe verificada; sem .mcp.json).
- [ ] v13.9: coletar friccoes de USO REAL do dono (terminal, web e Claude
      Code) -> correcoes.
- [ ] Reavaliar qwen2.5-coder como LILO_MODEL_FAST se o template de tools
      for corrigido em Ollama futuro (hoje: familia qwen3).

## Decisoes-chave (MANUAL)

- **Reset radical aprovado (24/08)**: legado v12.x (42k LOC) demolido; TUDO
  recuperavel no branch `v12.15-legado`. Plano completo na sessao de 24/08.
- 100% offline: so Ollama; nuvem NAO existe no nucleo (provider pluggavel
  poderia voltar como tool em v13.x).
- CLI unico (`lilo`); sem Streamlit/API/MCP no nucleo. **Emenda do dono
  (26/08, v13.7)**: interface web VOLTOU como SUBCOMANDO `lilo web` (stdlib,
  mesmo motor/portao) — "um binario" e anti-inchaco continuam de pe; o que
  segue proibido e entry point/servico/framework separado.
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
