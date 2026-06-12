# Integração com R (resultados e figuras via Docker)

Quando um projeto gera resultados/figuras em **R**, a skill executa esses
scripts **dentro do seu container Docker** e os trata como etapas reprodutíveis
do paper — no mesmo padrão idempotente das figuras Python.

## Convenção de diretórios

```
<RAIZ>/PAPER/
├── r/            # scripts R (.R) — geram figuras/tabelas
├── tools/        # scripts Python (fig_*.py, tab_*.py)
├── figuras/      # saídas de imagem (PNG/PDF/SVG)  <- R e Python escrevem aqui
├── tabelas/      # saídas tabulares (TSV ou .md pandoc)
└── src/          # fonte do manuscrito (.md)
```

Cada script (R ou Python) deve ser **idempotente**: lê os dados, grava a saída
em `PAPER/figuras/` ou `PAPER/tabelas/` e não edita os `.md`. Caminhos sempre
**relativos à raiz do projeto** (dentro do container, a raiz é montada em
`/project`).

## Como rodar

Regenerar tudo (R no Docker + Python) e depois montar:
```bash
bash ~/.claude/skills/build_paper/assets/figuras_rebuild.sh "<RAIZ>"
bash ~/.claude/skills/build_paper/assets/build.sh "<RAIZ>"
```

Rodar um único script R:
```bash
BUILD_PAPER_R_IMAGE=meu_lab/r-genetica:1.0 \
bash ~/.claude/skills/build_paper/assets/run_r.sh "<RAIZ>" PAPER/r/fig_pca.R
```

## Configuração do container (variáveis de ambiente)

| Variável | Default | Para quê |
|---|---|---|
| `BUILD_PAPER_R_IMAGE` | `rocker/tidyverse:latest` | sua imagem R |
| `BUILD_PAPER_R_MOUNT` | `/project` | onde a raiz é montada no container |
| `BUILD_PAPER_R_DOCKER` | `docker` | binário (ex.: `podman`) |
| `BUILD_PAPER_R_ARGS` | — | extras p/ `docker run` (`--gpus all`, `-e VAR=...`) |
| `BUILD_PAPER_R_USER` | — | `--user` (no Linux, `$(id -u):$(id -g)` evita arquivos root) |

Defina-as uma vez na sessão (ou num `.env`/script de projeto) para não repetir.

## Exemplo mínimo de script R (`PAPER/r/fig_pca.R`)

```r
# lê dados do projeto e grava a figura em PAPER/figuras/ (relativo à raiz=/project)
suppressMessages(library(ggplot2))
df  <- read.csv("dados/resultados.csv")
p   <- ggplot(df, aes(PC1, PC2, color = grupo)) + geom_point(size = 2) + theme_bw()
dir.create("PAPER/figuras", showWarnings = FALSE, recursive = TRUE)
ggsave("PAPER/figuras/Fig2_pca.png", p, width = 6, height = 4, dpi = 300)
# tabela como TSV (entra no manuscrito; ver abaixo)
dir.create("PAPER/tabelas", showWarnings = FALSE, recursive = TRUE)
write.table(aggregate(. ~ grupo, df, mean), "PAPER/tabelas/tab1_medias.tsv",
            sep = "\t", row.names = FALSE, quote = FALSE)
```

## Como as saídas entram no manuscrito

- **Figuras:** referencie pelo caminho relativo na fonte `.md`, ex.:
  `![Legenda da figura.](../figuras/Fig2_pca.png)`. O `build.sh` já inclui
  `--resource-path` apontando para `figuras/`, então DOCX/PDF/TEX as embutem.
- **Tabelas:** o R/Python grava um TSV em `PAPER/tabelas/`; um pequeno passo
  converte o TSV em **tabela pandoc** (pipe table) e a insere na fonte `.md`
  (mesmo padrão do projeto: script reexecutável que regenera a tabela se os
  dados mudarem). Alternativamente, o script pode gravar direto um `.md` com a
  tabela já formatada e você a inclui na seção de Resultados.

## Observações no Windows

- O `run_r.sh` define `MSYS_NO_PATHCONV=1` para o Git Bash não converter
  `/project`. Em geral o Docker Desktop aceita a montagem `-v C:/caminho:/project`.
- Se a montagem falhar, confirme que o drive está compartilhado no Docker
  Desktop (Settings → Resources → File Sharing).
- Reprodutibilidade: fixe a **tag** da imagem (ex.: `:1.0`), não `:latest`, para
  resultados estáveis ao longo das rodadas.
