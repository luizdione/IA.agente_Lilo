#!/usr/bin/env bash
# run_r.sh <RAIZ_DO_PROJETO> <script.R relativo à raiz> [args...]
# Executa um script R DENTRO do seu container Docker, montando o projeto.
# Reprodutível e idempotente: o script R deve escrever saídas em
# PAPER/figuras/ e/ou PAPER/tabelas/ (caminhos relativos à raiz do projeto).
#
# Config por variáveis de ambiente (todas com default):
#   BUILD_PAPER_R_IMAGE   imagem Docker            (default: rocker/tidyverse:latest)
#   BUILD_PAPER_R_MOUNT   ponto de montagem        (default: /project)
#   BUILD_PAPER_R_DOCKER  binário docker           (default: docker)
#   BUILD_PAPER_R_ARGS    args extras p/ docker run (ex.: "--gpus all" ou "-e VAR=1")
#   BUILD_PAPER_R_USER    usuário no container     (ex.: "$(id -u):$(id -g)" no Linux)
#
# Ex.: BUILD_PAPER_R_IMAGE=meu_lab/r-genetica:1.0 \
#      bash run_r.sh "C:/.../meu_projeto" PAPER/r/fig_pca.R
set -u
export MSYS_NO_PATHCONV=1   # impede o Git Bash de mutilar caminhos /project
ROOT="${1:?uso: run_r.sh <raiz> <script.R relativo> [args]}"
SCRIPT="${2:?caminho do .R relativo à raiz do projeto, ex. PAPER/r/fig.R}"
shift 2 || true

IMG="${BUILD_PAPER_R_IMAGE:-rocker/tidyverse:latest}"
MNT="${BUILD_PAPER_R_MOUNT:-/project}"
DOCKER="${BUILD_PAPER_R_DOCKER:-docker}"
EXTRA="${BUILD_PAPER_R_ARGS:-}"
USERFLAG=""; [ -n "${BUILD_PAPER_R_USER:-}" ] && USERFLAG="--user ${BUILD_PAPER_R_USER}"

command -v "$DOCKER" >/dev/null 2>&1 || { echo "ERRO: '$DOCKER' não encontrado no PATH."; exit 1; }
[ -f "$ROOT/$SCRIPT" ] || { echo "ERRO: script R não existe: $ROOT/$SCRIPT"; exit 1; }

echo "R(docker): $IMG  ::  $SCRIPT"
# shellcheck disable=SC2086
"$DOCKER" run --rm $USERFLAG $EXTRA \
  -v "$ROOT":"$MNT" -w "$MNT" \
  "$IMG" Rscript "$MNT/$SCRIPT" "$@"
