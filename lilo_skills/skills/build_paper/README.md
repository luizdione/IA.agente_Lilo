# build_paper

Skill genérica de **escrita e montagem de artigos científicos** para
bioquímica, biologia celular, ômicas (genômica, transcriptômica, proteômica,
metabolômica, epigenômica), genética animal, parasitologia, biologia molecular
e farmacologia — para qualquer periódico.

Transforma dados/resultados em manuscrito publicável e o monta de uma **fonte
única Markdown** para **DOCX, PDF e TEX**, com rigor científico, versionamento
reprodutível e **calibração ao periódico-alvo** via perfis de revista aprendidos
de fontes legítimas.

## Entregáveis (padrão)

Para cada manuscrito, dois pares × três formatos:

- **EN — submissão — limpa:** `manuscript_EN_submission.{docx,pdf,tex}`.
- **PT — análise/auditoria — marcada:** `manuscrito_PT_analise.{docx,pdf,tex}`,
  com banner vermelho `[VERSÃO DE ANÁLISE E CORREÇÃO — PORTUGUÊS — NÃO SUBMETER]`
  e a caixa "Notas de análise e correção". Nunca é submetida.

## Estrutura

```
build_paper/
├── SKILL.md                       # orquestrador (fluxo de 7 passos)
├── README.md
├── reference/                     # princípios, estrutura, build, periódicos, build_e_logistica
├── assets/
│   ├── manuscrito_template.md     # esqueleto da fonte (YAML + seções)
│   ├── marcar_versao_analise.py   # banner/caixa de auditoria (PT)
│   ├── build.sh                   # build bilíngue + hook GA + mirror de submissão
│   ├── figuras_rebuild.sh         # regenera figuras/tabelas (R via Docker + Python)
│   ├── nova_rodada.sh             # arquiva versões + abre log
│   ├── make_ga_prompt.py          # gera prompt FigureLabs/BioRender + insere na p.1 do docx
│   └── ga_icons.py                # biblioteca de ícones vetoriais (fallback do GA)
├── scripts/checar_profundidade.py
├── journals/registry.json         # portfólio de revistas-alvo
├── journals/profiles/*.json       # perfis aprendidos (gerados)
└── ml/                            # build_journal_profile.py (+ requirements.txt) e via R
```

## Dependências

### Sistema (obrigatório para o build)
- **pandoc** ≥ 3.0 — converte Markdown → DOCX/TEX/PDF.
- **tectonic** — motor LaTeX para o PDF (baixa pacotes sob demanda).
- Uma fonte com cobertura Unicode ampla para símbolos científicos
  (≤ ≥ ≈ × · Å µ). Padrão: **Cambria** (override por `MAINFONT`).

No setup do autor, ambos vivem no env conda `datascience` (Miniforge3). Em
qualquer máquina, o `build.sh` detecta via PATH; sobrescreva com variáveis:
`PANDOC=`, `PDF_ENGINE=`, `PY=`, `MAINFONT=`, `BUILD_PAPER_CONDA_BIN=`.

### Python
- **Núcleo da skill** (marcar/checar): só biblioteca padrão — nada a instalar.
- **Pipeline de perfis de revista** (`ml/`): `pip install -r ml/requirements.txt`
  - obrigatório: `requests`
  - opcionais: `pdfplumber` (PDFs locais), `lxml` (JATS), `numpy`, `scikit-learn`
  - pesados/opcionais: `sentence-transformers`, `spacy` (+ modelo)

### R (opcional — via alternativa de análise de corpus)
Para quem prefere o ecossistema R para bibliometria e mineração de texto, há um
caminho paralelo (ver `ml/build_journal_profile_R.R`):

```r
install.packages(c(
  "openalexR",   # consulta OpenAlex (metadados + abstracts) por ISSN
  "rcrossref",   # metadados Crossref
  "europepmc",   # texto integral OA (Europe PMC)
  "bibliometrix",# análise bibliométrica (autores, refs, redes)
  "tidytext",    # tokenização, n-gramas, tf-idf
  "quanteda",    # corpus, KWIC, lexmetria, complexidade de frase
  "pdftools",    # extrair texto de PDFs locais (acesso legítimo)
  "tidyverse"
))
```

Equivalências com a via Python:
- contagem por seção / abstract → `tidytext`/`quanteda` (tokens, n de sentenças).
- estilo de citação e densidade → regex em `quanteda::kwic` + `bibliometrix`.
- padrões semânticos (conectivos, aberturas) → `tidytext` (n-gramas, tf-idf).
- redes de coautoria/citação → `bibliometrix::biblioAnalysis`/`networkPlot`.

As duas vias gravam o mesmo formato em `journals/profiles/<revista>.json`, então
a skill consome qualquer uma indistintamente.

## Instalação

### Como skill (nível usuário)
Copie a pasta para `~/.claude/skills/build_paper/`. Ela é acionada
automaticamente quando você pede para escrever/montar um artigo.

### Como comando
`~/.claude/commands/build_paper.md` cria o atalho **`/build_paper`** (Claude
Code) — invoca a versão genérica, ignorando scripts específicos do projeto.

### Como plugin (produto / clientes)
Empacotada como plugin do Claude Code + marketplace (repo GitHub):
```
/plugin marketplace add SEU_USUARIO_GITHUB/build-paper-plugin
/plugin install build-paper@melo-science-tools
```
Clientes precisam de pandoc + tectonic + Python (e, p/ perfis, os pacotes de
`ml/requirements.txt`; opcionalmente R).

## Uso

```bash
# 1) escrever: peça "monta o paper para a <revista>" ou use /build_paper
# 2) aprender o estilo da revista-alvo (fontes legítimas):
python ml/build_journal_profile.py --name "Acta Tropica" --n 10 --mailto voce@ex.com
# 3) montar os 6 arquivos:
bash assets/build.sh "<RAIZ_DO_PROJETO>" --submit "<PASTA_SUBMISSAO>"
# 4) nova rodada de revisão:
bash assets/nova_rodada.sh "<RAIZ_DO_PROJETO>" "<foco>"
# 5) conferir profundidade:
python scripts/checar_profundidade.py PAPER/src/manuscrito_PT.md --abstract-max 250
```

## Perfis de revista e direitos autorais

Os perfis são aprendidos **apenas de fontes legítimas**: OpenAlex/Crossref
(metadados + abstracts), Europe PMC (texto integral de artigos **open-access**)
e PDFs locais a que o usuário tenha **acesso legítimo** (`--local-pdfs`). A
ferramenta **não** baixa nem armazena PDFs pagos sob paywall. As "normas de
seção" são **estatísticas empíricas** (mediana/percentis) do corpus amostrado —
não são regras do periódico; os limites oficiais (abstract, total, estilo de
referências) devem ser confirmados no *Guide for Authors* de cada revista.

## Logística de submissão (mirror self-compilable)

Cada projeto mantém **uma pasta de submissão** em
`OneDrive/.../artigos_submissao/<projeto>/`. A regra (gravada na memória do
autor) é: **sempre sobrescrever** essa pasta com a versão mais nova (DOCX + TEX +
PDF + `figures/`); versões antigas vão para `OBSOLETOS/` na raiz do projeto.

O mirror é **self-compilable** — abre e compila tanto na origem quanto na pasta
de submissão, sem ajustes manuais:

- **`\graphicspath`** robusto, cobrindo os dois layouts de pasta:
  `{{../figures/}{figures/}{../figuras/}{figuras/}{./}}`.
- **`references.bib`** é copiado junto (senão o `\bibliography` quebra na cópia).
- Cópia **resiliente** (try/except por arquivo): pula arquivos travados (PDF
  aberto no viewer) sem abortar o build.

> ⚠️ **Nunca** use casamento difuso por basename ao sincronizar figuras entre
> projetos. `manuscript_EN.tex` existe em vários projetos e o Windows é
> case-insensitive — isso já causou contaminação cruzada (PDFs de *genomas*
> sobre os de *naftoquinona*). O utilitário
> `artigos_submissao/_make_selfcompilable.py` usa **SRC_MAP explícito** +
> exclusão por prefixo de entregável (`manuscript_`/`supplementary_`/`manual_`).

## Convenção de nomes (slug)

Para evitar colisões entre projetos na pasta de submissão, os entregáveis usam
**prefixo de slug**: `<slug>_manuscript_EN.{tex,docx,pdf}`. O slug é
parametrizável (ex.: `PAPER_SLUG`/`SLUG` no `build_paper.py` do projeto;
`2scnnq`, `genomas`, `kanon`, `rho`). Escopo do refactor: **vitrine + fonte +
build** de cada projeto, mantendo as especificidades de cada um.

## Graphical abstract — 3 alternativas (cascata)

A skill produz o graphical abstract por **prioridade decrescente**, atualizando
a cada versão do paper:

1. **Override manual (BioRender / FigureLabs):** se existir
   `graphical_abstract_manual.pdf` no projeto, ele é usado tal-e-qual. É o
   caminho de maior qualidade — figura feita no editor BioRender/FigureLabs.
2. **Fallback vetorial data-aware (`make_graphical_abstract.py` + `ga_icons.py`):**
   na ausência do override, gera um GA vetorial a partir dos dados reais
   (`canonical_data.json`, modo de ligação) com ícones científicos
   (`ga_icons.py`: camundongo, bovino, tripanossoma, *Leishmania*, mitocôndria,
   célula hospedeira, surto de ROS, DNA, setas de fluxo/ciclo).
3. **Prompt para IA (`make_ga_prompt.py`):** lê
   `graphical_abstract.config.json` e gera um **prompt pronto** para colar em
   <https://chat.figurelabs.ai/> (BioRender AI). Grava
   `<slug>_GRAPHICAL_ABSTRACT_PROMPT.{md,txt}` **e insere o prompt como caixa na
   1ª página de cada `.docx`** da submissão (ponto de partida para o autor gerar
   a arte e salvá-la como `graphical_abstract_manual.pdf` → vira a opção 1 na
   próxima rodada).

### `graphical_abstract.config.json`

Fonte única do prompt (e do GA vetorial). Campos:

```json
{
  "slug": "2scnnq",
  "title": "…título do estudo…",
  "key_numbers": ["IC50 = … µM", "LIG→FAD 2.6 Å", "…"],
  "biorender_terms": ["Trypanosoma cruzi", "mitochondrion", "ROS", "…"],
  "story_flow": ["composto", "→ alvo TcTR", "→ mecanismo dual", "→ efeito"]
}
```

O `make_ga_prompt.py` é **idempotente**: ao reinserir o prompt num docx, remove
primeiro o bloco anterior (marcadores `▶ PROMPT — Graphical abstract` …
`(Gerado/atualizado a cada build`), evitando empilhamento em re-execuções.

> O BioRender MCP é **somente busca** (`search-icons`/`search-templates`) — não
> edita nem exporta, e os ícones são proprietários. Por isso o caminho de
> qualidade é o override manual (opção 1) e o prompt (opção 3) alimenta o autor.

## Como cada projeto dispara o GA + mirror

Não há um único entrypoint: cada projeto usa o que tem. Todos chamam o **mesmo**
`assets/make_ga_prompt.py` da skill (fonte única).

| Projeto | Entrypoint | Mecanismo do GA |
|---|---|---|
| **2-SCN-NQ (naftoquinona)** | `PAPER/scripts/build_paper.py` | hook integrado: regenera GA → compila → insere prompt → `mirror_submission()` |
| **Rho (dois_híbridos)** | `PAPER/build.sh` | hook após `build_one` → insere prompt nos docx → sync submissão |
| **genomas** | `results/paper/integrado/refresh_ga_prompt.py` | wrapper: roda `make_ga_prompt` sobre os docx da submissão (exclui `supplementary*`) |
| **kanon-index** | `artigo_poster/refresh_ga_prompt.py` | idem genomas |
| **genérico (skill)** | `assets/build.sh` | hook detecta `graphical_abstract.config.json` em `PAPER/`, raiz ou `src/` → insere prompt → copia para `--submit` |

Os `refresh_ga_prompt.py` (genomas/kanon) existem porque esses projetos rodam
via pipeline **Cowork** e não têm build script próprio — podem ser chamados pelo
pipeline ou rodados à mão a cada versão:

```bash
python refresh_ga_prompt.py
# equivale a: python make_ga_prompt.py graphical_abstract.config.json \
#               --out <submissão> --docx <submissão>/*.docx
```

## Fluxo ponta-a-ponta (resumo)

```
fonte única .md  ──pandoc──►  DOCX / TEX / PDF (EN limpo + PT marcado)
       │                              │
   figuras reprodutíveis          [hook GA] override pdf > vetorial > prompt
   (R via Docker / Python)            │
       │                         insere prompt na p.1 dos docx
       └──────────────►  mirror self-compilable → artigos_submissao/<projeto>/
                          (graphicspath robusto + references.bib + figures/)
                          versões antigas → OBSOLETOS/
```

## Licença
MIT (ver `LICENSE` no pacote do plugin).
