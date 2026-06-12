---
name: build_paper
description: >-
  Escrita científica de artigos e manuscritos para publicação nas áreas de
  bioquímica, biologia celular, ômicas (genômica, transcriptômica, proteômica,
  metabolômica, epigenômica), genética animal, parasitologia, biologia
  molecular e farmacologia — para qualquer periódico. Acione esta skill em
  pedidos como "escrever um paper", "montar/redigir o manuscrito", "redação
  científica", "build paper", "/build_paper", "gerar Introdução/Métodos/
  Resultados/Discussão/Abstract", "transformar resultados em artigo", "preparar
  o artigo para o periódico X", "expandir/aprofundar uma seção" ou "responder a
  revisores", e ao trabalhar com uma fonte Markdown de manuscrito. Entrega
  bilíngue por padrão: versão EN limpa para submissão + versão PT marcada para
  análise/auditoria, cada uma em DOCX, PDF e TEX. Usa perfis de revista
  (aprendidos de fontes legítimas: OpenAlex/Europe PMC) para calibrar tamanho de
  seções, estilo de citação e padrões de escrita ao periódico-alvo, e integra
  resultados/figuras gerados em R (via Docker) ou Python. Cobre o fluxo
  completo: fonte única Markdown -> DOCX/TEX/PDF (pandoc + tectonic),
  versionamento por rodadas, figuras e tabelas reprodutíveis. Genérica: não é
  específica de um projeto em particular.
---

# build_paper — Escrita e montagem de artigos científicos

## O que esta skill faz

Transforma dados/resultados em um **manuscrito publicável** e o **monta** de uma
fonte única Markdown para os formatos finais (DOCX, PDF, TEX), com rigor
científico, versionamento reprodutível e calibração ao periódico-alvo.

**Áreas:** bioquímica, biologia celular, ômicas (genômica, transcriptômica,
proteômica, metabolômica, epigenômica), genética animal, parasitologia,
biologia molecular e farmacologia.

Eixos: **redação** (conteúdo/rigor), **calibração ao periódico** (perfis de
revista), **integração de análises** (R via Docker e/ou Python) e
**build/logística** (produção dos arquivos + versionamento).

## Entregáveis (padrão obrigatório)

Dois pares, três formatos cada (DOCX, PDF, TEX):
- **EN — submissão — LIMPA:** `manuscript_EN_submission.{docx,pdf,tex}`.
- **PT — análise/auditoria — MARCADA:** `manuscrito_PT_analise.{docx,pdf,tex}`
  com banner vermelho `[VERSÃO DE ANÁLISE E CORREÇÃO — PORTUGUÊS — NÃO SUBMETER]`
  e caixa "Notas de análise e correção". Nunca é submetida.

A marcação é injetada automaticamente pelo `assets/marcar_versao_analise.py`
(invocado pelo `build.sh`); a fonte PT permanece limpa. Regra: `reference/periodicos.md`.

## Fluxo de trabalho

### Passo 0 — Contexto + periódico-alvo
Reúna dados/resultados/figuras/rascunhos. Defina periódico-alvo, idiomas
(default EN+PT) e tipo de artigo. **Carregue o perfil da revista** se existir em
`journals/profiles/<revista>.json`.

### Passo 1 — Estrutura e profundidade (LEITURA OBRIGATÓRIA)
**Sempre leia e aplique `reference/estrutura_e_profundidade.md` antes de redigir
ou revisar qualquer seção** — é parte não-opcional desta skill. Ele define:
metas mínimas de profundidade por seção; estrutura canônica (IMRaD + Declarações);
**tempos verbais por seção**; **pessoa gramatical** (autor único → 1ª pessoa do
singular); e o **Signposting / coesão narrativa** — terminar cada subseção de
Resultados e cada virada da Discussão com uma frase-ponte para a seguinte, evitando
"parágrafos-ilha" (efeito fast-food de LLM). Se houver perfil de revista, prefira
suas normas empíricas por seção e o teto de abstract do Guide for Authors.

### Passo 2 — Redigir com rigor
`reference/principios_cientificos.md`: distinguir fato/interpretação/
especulação; limitações; hipóteses alternativas; nunca causalidade de
correlação; **nunca inventar números/referências**. Siga o estilo de citação e
padrões semânticos do perfil quando disponível.

### Passo 3 — Fonte única Markdown
Edite só `PAPER/src/manuscrito_{EN,PT}.md` (base: `assets/manuscrito_template.md`).
DOCX/PDF/TEX são derivados.

### Passo 4 — Figuras e tabelas reprodutíveis (R e/ou Python)
Scripts idempotentes a partir dos dados reais. R roda no seu **container Docker**;
Python local. Regenere tudo com:
`bash assets/figuras_rebuild.sh "<RAIZ>"` (executa `PAPER/r/*.R` via Docker +
`PAPER/tools/fig_*.py`/`tab_*.py` -> `PAPER/figuras/`, `PAPER/tabelas/`).
Detalhes e config do container: `reference/integracao_R.md`.

### Passo 4b — Graphical abstract / TOC graphic (FigureLabs)
Gere o *graphical abstract* no **chat.figurelabs.ai** (modo Scientific Illustration,
Nano Banana Pro) e ligue-o ao TEX (`\begin{tocentry}` no achemso, ou figura de TOC)
para fluir a PDF+DOCX no rebuild. Procedimento completo, *prompt-recipe*, checagem
científica obrigatória da imagem e o **limite de acesso** (human-in-the-loop via
extensão Claude-in-Chrome na sua sessão já logada — **sem credenciais autônomas /
sem geração desacompanhada**): `reference/graphical_abstract_figurelabs.md`.
Salve como `graphical_abstract_figurelabs.png` (nome distinto p/ não ser
sobrescrito pelo GA auto-gerado por script). Vale para todos os projetos.

### Passo 5 — Build
`bash assets/build.sh "<RAIZ>" [--submit "<pasta>"]` (portável; detecta
pandoc/tectonic/python via PATH; overridable por variáveis — ver
`reference/build_e_logistica.md`).

### Passo 6 — Versionar
`bash assets/nova_rodada.sh "<RAIZ>" "<foco>"`.

### Passo 7 — Conferir
`python scripts/checar_profundidade.py PAPER/src/manuscrito_PT.md --abstract-max <teto>`;
referências reais; normas do periódico; **EN limpa final**. Confira contra
`reference/estrutura_e_profundidade.md`: tempos verbais por seção, pessoa gramatical
e **signposting** — cada subseção de Resultados e cada virada da Discussão termina com
frase-ponte; nenhum "parágrafo-ilha". Aplique as correções nas DUAS versões (EN e PT).

## Perfis de revista (calibração por ML)

`ml/build_journal_profile.py` aprende o estilo de um periódico de **fontes
legítimas** (OpenAlex/Crossref: metadados+abstracts; Europe PMC: texto integral
de artigos OPEN-ACCESS; PDFs locais via `--local-pdfs`). **Não baixa PDFs pagos.**
Gera `journals/profiles/<revista>.json` (normas de seção empíricas, estilo de
citação, nº de referências, padrões semânticos).

```bash
python ml/build_journal_profile.py --list
python ml/build_journal_profile.py --issn 0001-706X --n 10 --mailto voce@ex.com
python ml/build_journal_profile.py --update
```
Revistas em `journals/registry.json`. Ao redigir, **leia o perfil da revista-alvo
e aplique-o**.

## Arquivos desta skill

| Arquivo | Conteúdo |
|---|---|
| `reference/principios_cientificos.md` | Rigor, integração de evidências, qualidade |
| `reference/estrutura_e_profundidade.md` | **(leitura obrigatória)** Estrutura das seções + metas de profundidade + tempos verbais + pessoa gramatical + **signposting** (coesão narrativa, sem parágrafos-ilha) |
| `reference/build_e_logistica.md` | Build, versionamento, troubleshooting, variáveis |
| `reference/periodicos.md` | Áreas, regra bilíngue, banner/caixa, perfis de periódico |
| `reference/integracao_R.md` | Integração R via Docker (figuras/tabelas) |
| `reference/graphical_abstract_figurelabs.md` | Graphical abstract via FigureLabs (chat.figurelabs.ai): procedimento, prompt, checagem, limite de acesso |
| `assets/manuscrito_template.md` | Esqueleto da fonte (YAML + seções + notação) |
| `assets/marcar_versao_analise.py` | Injeta/remove banner + caixa de auditoria (PT) |
| `assets/build.sh` | Build bilíngue MD -> DOCX/PDF/TEX (portável) |
| `assets/figuras_rebuild.sh` | Regenera figuras/tabelas (R via Docker + Python) |
| `assets/run_r.sh` | Executa um script R dentro do container Docker |
| `assets/nova_rodada.sh` | Arquivar versões + abrir entrada no log |
| `scripts/checar_profundidade.py` | Palavras por seção vs metas |
| `journals/registry.json` | Portfólio de revistas-alvo (ISSN, área, OA) |
| `ml/build_journal_profile.py` | Aprende perfis de estilo por revista (fontes legítimas) |

## Princípio condutor

Profundidade e rigor científico acima de concisão. Discussão ≥ Resultados em
profundidade. Conclusões proporcionais às evidências; limitações explícitas;
nada de números inventados. Qualidade compatível com revisão por pares.
