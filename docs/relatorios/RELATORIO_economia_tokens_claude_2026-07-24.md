# Relatório — Economia de tokens **do Claude** (FASE 0–3) — 2026-07-24

> Execução autônoma noturna. Objetivo: reduzir o consumo de tokens **do Claude**
> (Anthropic), aproveitando **só a FASE 4** do documento externo *"LILO Auditoria
> e Otimização"* (a única parte que trata da superfície MCP → Claude; as fases de
> VRAM/cache/segurança daquele doc são de outra topologia ou de ganho puramente
> local e foram descartadas). Código em `C:\github\IA.agente_Lilo` (arch-v11).

## ⚠️ Ação necessária ao acordar
1. **Reiniciar o Claude Code** (fechar e reabrir a sessão/app). Só então o novo
   perfil MCP vigora: os *vazadores* (`fs_read`, `fs_batch_read`, `grep_and_read`,
   `run_shell`, `run_python`, `fs_write/codemod`, `lilo_web_*`, `lilo_chat`,
   `lilo_sql`) somem do contexto e as 2 tools novas aparecem.
2. **Revisar o diff no arch-v11 e commitar quando quiser.** Nada foi commitado —
   minhas mudanças somam-se às 463 já pendentes (V18/V19). Sugestão de branch:
   `audit/economia-tokens-claude`.

## O que foi feito (com provas)

### FASE 0 — Fazer o perfil `claude_code` vigorar (maior ganho, custo ~zero)
**Causa-raiz:** o registro `lilo` **global** em `~/.claude.json` rodava
`lilo_mcp.py` **sem `--profile` e sem `LILO_SERVER_PROFILE`** → caía no default
`desktop` = **todas as tools**. Por isso os dumps brutos e as duplicatas do
Read/Grep/Bash nativos entravam no contexto de toda requisição.

**Correção (reversível):**
- `~/.claude.json` → registro `lilo` reapontado para `C:\github\IA.agente_Lilo\lilo_mcp.py`
  com `--profile claude_code` e `LILO_SERVER_PROFILE=claude_code`.
  Backup: `C:\Users\luizd\.claude.json.bak-20260724-001250`.
- `.mcp.json` do projeto → reapontado para o github (consistência).

**Prova:** com `claude_code`, o servidor carrega **43 tools** e **0 vazadores**
(`fs_read`/`fs_batch_read`/`grep_and_read`/`run_shell`/`run_python`/`lilo_web_*`
ausentes). Antes (default `desktop`): todas as tools + dumps de até 200 KB.

### FASE 1 — `lilo_summarize_file` (destilar arquivos locais) — *prioridade #1*
Nova tool + módulo `shared/summarize.py`: lê **qualquer** arquivo de texto
(`.log/.out/.txt/.csv/.json/código`, e PDFs via PyMuPDF/pdfminer), destila pelo
**Ollama LOCAL** (tier forçado — nunca gasta Claude) e devolve só o resumo. Recorte
head+tail preserva início e fim de logs; teto de saída configurável.
Reusa `PDFAgent._summarize_file` (padrão) + `shared/llm_client.get_client`.

**Prova (end-to-end via gemma3:12b):** log de 9186 chars → resumo de 930 chars =
**redução de 90%**, capturando corretamente as amostras que falharam. O bruto
não entrou no contexto.

### FASE 2 — `parse_bio_log` (parsers de log bioinfo) — *prioridade #2*
Nova tool + módulo `shared/bioparsers.py` (Python puro, sem LLM, sem deps novas):
1 tool com **auto-detecção** e 4 parsers → tabela compacta:
- `vina` (AutoDock Vina) → afinidades kcal/mol + RMSD + melhor pose
- `qpcr` (export csv/tsv) → Cq por amostra (agrupa por Sample/Target) + eficiência/R²/slope
- `fastqc` (fastqc_data.txt / summary.txt) → módulos PASS/WARN/FAIL
- `vcf` → contagens por tipo de variante, Ti/Tv, por cromossomo

**Prova (amostras sintéticas):** Vina melhor pose −9.20; FastQC 1 PASS/1 WARN/1 FAIL;
VCF 3 SNP/1 indel, **Ti/Tv=2.00**; qPCR agrupou por `Ctrl/Trat` e descartou
`Undetermined`. Ganho típico: ~3000 tokens de log → ~150 de tabela.

### FASE 3 — Scholar com DOI (digest) — *prioridade #3*
`ScholarAgent._format_results` agora exibe **DOI** quando disponível (novo helper
`_extract_doi`, extrai de doi/id/url por regex). Melhoria mínima e segura: o
scholar **já** é frugal (RAG/síntese, não despeja PDFs). Um digest "1 parágrafo
destilado por artigo" completo exigiria buscar **abstracts** (os resultados atuais
não os trazem) — deixado como próximo passo.

**Prova:** artigo com DOI mostra `DOI: 10.1234/...`; sem DOI, só a URL (sem inventar).

## Arquivos
**Criados:** `shared/summarize.py`, `shared/bioparsers.py`
**Modificados:** `lilo_mcp.py` (2 tools + `_PROFILE_TOOLS['claude_code']`),
`config/profiles.yaml` (mcp_tools do `claude_code`),
`tests/test_tool_surface.py` (GOLDEN_PROFILE_TOOLS), `agents/scholaragent/agent.py`
**Config (fora do repo):** `~/.claude.json` (+ backup), `.mcp.json` do projeto

## Testes
`test_tool_surface` + `test_routing_golden` + `test_router`: **14 passed, 2 skipped**.
`smoke_test_v11.py`: **13/13** (item 13 confirma `claude_code` = 43 tools).

## Ficou de fora (backlog)
- **FASE 4 (telemetria da superfície MCP):** não priorizada; contaria chars/tokens
  da resposta de cada tool em `handle_tool_call` para medir antes/depois.
- **Digest com abstracts** (1 parágrafo destilado por artigo).
- **Expor `lilo_summarize_file`/`parse_bio_log` a outros perfis** (bio/opus/pycharm),
  se quiser usá-las também no Desktop/PyCharm.

## Reverter
- Config MCP: restaurar `C:\Users\luizd\.claude.json.bak-20260724-001250`.
- Código: `git checkout -- <arquivo>` no arch-v11 (nada commitado).
