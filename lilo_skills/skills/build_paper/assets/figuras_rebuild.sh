#!/usr/bin/env bash
# figuras_rebuild.sh <RAIZ_DO_PROJETO>
# Regenera figuras e tabelas de forma IDEMPOTENTE (só sobrescreve saídas, NÃO
# edita os .md). Depois rode build.sh. Executa, na ordem:
#   1) scripts R em  PAPER/r/*.R           -> via Docker (run_r.sh)
#   2) scripts Python em PAPER/tools/fig_*.py e PAPER/tools/tab_*.py
# Convenção: cada script grava em PAPER/figuras/ (PNG/PDF/SVG) e/ou
# PAPER/tabelas/ (TSV ou .md pandoc), com caminhos relativos à raiz.
set -u
ROOT="${1:?uso: figuras_rebuild.sh <raiz>}"
SK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python (mesma detecção do build.sh)
PY="${PY:-}"
if [ -z "$PY" ]; then
  for c in "C:/Users/luizd/miniforge3/envs/datascience/python.exe" python3 python; do
    command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; [ -x "$c" ] && { PY="$c"; break; }
  done
fi

mkdir -p "$ROOT/PAPER/figuras" "$ROOT/PAPER/tabelas"

echo "== 1) scripts R (Docker) =="
if [ -d "$ROOT/PAPER/r" ]; then
  shopt -s nullglob
  for r in "$ROOT/PAPER/r"/*.R; do
    rel="PAPER/r/$(basename "$r")"
    bash "$SK/run_r.sh" "$ROOT" "$rel" || echo "  (falhou: $rel)"
  done
  shopt -u nullglob
else
  echo "  (sem PAPER/r/ — pulado)"
fi

echo "== 2) scripts Python =="
if [ -d "$ROOT/PAPER/tools" ]; then
  shopt -s nullglob
  for p in "$ROOT/PAPER/tools"/fig_*.py "$ROOT/PAPER/tools"/tab_*.py; do
    echo "PY: $(basename "$p")"
    "$PY" "$p" || echo "  (falhou: $(basename "$p"))"
  done
  shopt -u nullglob
else
  echo "  (sem PAPER/tools/ — pulado)"
fi

echo "== saídas =="
ls "$ROOT/PAPER/figuras" 2>/dev/null
ls "$ROOT/PAPER/tabelas" 2>/dev/null
echo "Agora rode: bash $SK/build.sh \"$ROOT\""
