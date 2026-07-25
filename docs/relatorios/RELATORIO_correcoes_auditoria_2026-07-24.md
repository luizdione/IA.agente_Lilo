# Relatório — Correções da auditoria adversarial (V20.1) — 2026-07-24

Duas auditorias adversariais (cada achado verificado por um refutador independente):
- **Código V20 (fases 0-3):** 21 achados brutos → **18 confirmados**.
- **Últimos 5 dias (V17→V20):** 35 brutos → **19 confirmados** (dimensões *redundância* e *localhost* parcialmente interrompidas por limite de sessão).

## Corrigido e commitado (`7b1b472`, branch arch-v11)

### Parsers — `shared/bioparsers.py`
- **Vina 1.2.x**: RMSD inteiro (`0`) não descarta mais a **melhor pose (modo 1)**; avisa em lacuna de numeração; regex ancorada a uma única linha.
- **qPCR**: aceita **Cq com vírgula** (pt-BR); cabeçalho delimitado (ignora preâmbulo ABI/QuantStudio); **SD amostral** (n-1).
- **VCF**: ALT simbólico/gVCF (`<NON_REF>`/`<*>`/`<DEL>`) não é mais contado como indel.
- **FastQC**: passa a detectar `summary.txt`.

### Sumarizador — `shared/summarize.py`
- Erro de leitura **nunca vira "conteúdo"** destilado (não fabrica resumo).
- Detecção de binário por **sniff de conteúdo** (NUL / proporção não-texto), não por extensão.
- Teto de leitura em bytes (não materializa arquivo gigante); **clamp de `max_chars`**.

### Segurança — `lilo_mcp.py`
- `lilo_summarize_file` e `parse_bio_log` passam pela **allow-list `LILO_DESKTOP_ALLOW`** (a mesma dos `fs_*`, via `_is_path_allowed`), **fail-closed**. Deixaram de ser bypass de leitura de disco. *Testado:* arquivo no repo → permitido; `C:\Windows\...` → negado.

### Superfície MCP
- **8 configs** (`.mcp.json` + `config/mcp/*.json`) reapontados para `C:\github\IA.agente_Lilo`.
- `scholar_brain` adicionada ao YAML — estava **morta** em bio/cowork/claude_desktop/claude_code.
- `test_tool_surface.py`: novo teste de **consistência canal embarcado ↔ YAML** (pega tools que o YAML deixa mortas).

### Testes (cobertura era zero)
- `tests/shared/test_bioparsers.py` + `tests/shared/test_summarize.py` — **18 testes** travando os bugs acima.

**Provas:** suíte inteira `pytest tests/` verde; `smoke_test_v11` 13/13; perfil `claude_code` = **44 tools**, zero vazadores.

## Pendente (não aplicado)

| Item | Sev. | Nota |
|---|---|---|
| `_extract_doi` no-op em `source="auto"` | média | Corrigir na origem: popular `doi` em `shared/research_sources.py` (`_std` + cada `search_*`), em vez de regex no formatador |
| Router só ativa com `LILO_ROUTER=embed` | média | No default a cascata do villa (`_detect_domain`) ainda decide; a promessa de "matar as 3 cópias de keywords" não vigora no caminho padrão. Definir `LILO_ROUTER=embed` no `.env` após validar o golden-set |
| Docs congelados pré-V17 | média | CHANGELOG para em v12.5 (falta V18/V19/V20); README/`.env.example`/`config.yaml.example`/CLAUDE.md citam modelos/skills/`_ARCHIVE_v10`/arch-v10 que não existem mais |
| Gerador de skills obsoleto anunciado na UI | média | Reverteria a poda de ~200 skills da V19 |
| Registro de subagentes divergente | média | `lilo.py` vs `dashboard.py` (faltam 3 agentes na UI) |
| **Push de 5 commits** | — | origin está 5 commits atrás; OneDrive não serve de backup (pré-V17.3). Aguardando decisão do autor |

## Nota de reconciliação
O working tree estava **limpo** (V18/V19/V20 já commitada em `7f20255` pelo autor) — a premissa anterior de "460+ não-commitados" caiu. As correções acima entraram como o commit **novo** `7b1b472` por cima.
