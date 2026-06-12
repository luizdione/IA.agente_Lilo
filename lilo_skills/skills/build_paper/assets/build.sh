#!/usr/bin/env bash
# build.sh <RAIZ_DO_PROJETO> [--submit <PASTA_SUBMISSAO>]
# Monta, a partir de PAPER/src/manuscrito_*.md, os entregáveis em DOCX/TEX/PDF:
#   EN  -> manuscript_EN_submission.{docx,tex,pdf}   (LIMPA, para submissão)
#   PT  -> manuscrito_PT_analise.{docx,tex,pdf}       (banner + caixa, auditoria)
# Motor: pandoc (DOCX/TEX) + tectonic (PDF). Fonte PT permanece limpa: a
# marcação de auditoria é injetada numa cópia temporária só no build.
#
# PORTÁVEL: detecta pandoc/tectonic/python via PATH. Sobrescreva, se quiser:
#   PANDOC=...  PDF_ENGINE=...  PY=...  MAINFONT=...  BUILD_PAPER_CONDA_BIN=...
set -u
ROOT="${1:?uso: build.sh <RAIZ_DO_PROJETO> [--submit <pasta>]}"; shift || true
SUBMIT=""
while [ $# -gt 0 ]; do case "$1" in --submit) SUBMIT="${2:-}"; shift 2;; *) shift;; esac; done

# 1) se houver um env conda informado/conhecido, torna seus binários visíveis
CONDA_BIN="${BUILD_PAPER_CONDA_BIN:-C:/Users/luizd/miniforge3/envs/datascience/Library/bin}"
[ -d "$CONDA_BIN" ] && export PATH="$CONDA_BIN:$PATH"
# 2) interpretadores (PATH primeiro; depois caminhos conhecidos; sempre overridable)
PANDOC="${PANDOC:-$(command -v pandoc || true)}"
[ -z "$PANDOC" ] && [ -x "$CONDA_BIN/pandoc.exe" ] && PANDOC="$CONDA_BIN/pandoc.exe"
PDF_ENGINE="${PDF_ENGINE:-$(command -v tectonic || true)}"
[ -z "$PDF_ENGINE" ] && PDF_ENGINE="tectonic"   # pandoc resolve no PATH se existir
MAINFONT="${MAINFONT:-Cambria}"
PY="${PY:-}"
if [ -z "$PY" ]; then
  for cand in "C:/Users/luizd/miniforge3/envs/datascience/python.exe" python3 python; do
    command -v "$cand" >/dev/null 2>&1 && { PY="$cand"; break; }
    [ -x "$cand" ] && { PY="$cand"; break; }
  done
fi
[ -z "$PANDOC" ] && { echo "ERRO: pandoc não encontrado (defina PANDOC=...)."; exit 1; }

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARK="$SKILL_DIR/marcar_versao_analise.py"
PAPER="$ROOT/PAPER"; SRC="$PAPER/src"; OUT="$PAPER/build"; FIG="$PAPER/figuras"
mkdir -p "$OUT"

common=( --resource-path=".:$SRC:$FIG" )
pdfopts=( --pdf-engine="$PDF_ENGINE" -V geometry:margin=2.5cm -V fontsize=11pt -V mainfont="$MAINFONT" )

emit () {  # emit <src.md> <basename>
  local src="$1" base="$2"
  [ -f "$src" ] || return 0
  echo "== $base =="
  "$PANDOC" "$src" -o "$OUT/$base.docx"    "${common[@]}" && echo "  DOCX ok" || echo "  DOCX FALHOU"
  "$PANDOC" "$src" -o "$OUT/$base.tex" -s  "${common[@]}" && echo "  TEX ok"  || echo "  TEX FALHOU"
  "$PANDOC" "$src" -o "$OUT/$base.pdf" "${pdfopts[@]}" "${common[@]}" \
     && echo "  PDF ok" || echo "  PDF FALHOU (cheque tectonic/mainfont)"
}

# EN — submissão (limpa)
for ensrc in "$SRC/manuscrito_EN.md" "$SRC/manuscript_EN.md"; do
  [ -f "$ensrc" ] && emit "$ensrc" "manuscript_EN_submission"
done
# PT — análise/auditoria (injeta banner+caixa numa cópia temporária)
for ptsrc in "$SRC/manuscrito_PT.md" "$SRC/manuscript_PT.md"; do
  [ -f "$ptsrc" ] || continue
  tmp="$OUT/.tmp_PT_analise.md"
  if [ -n "$PY" ] && [ -f "$MARK" ]; then "$PY" "$MARK" "$ptsrc" -o "$tmp" >/dev/null 2>&1 || cp "$ptsrc" "$tmp"
  else cp "$ptsrc" "$tmp"; fi
  emit "$tmp" "manuscrito_PT_analise"; rm -f "$tmp"
done

echo "== build/ =="; ls -la "$OUT" 2>/dev/null

# === Graphical abstract: prompt p/ IA (FigureLabs/BioRender) na 1a pagina dos docx ===
# Data-aware e atualizado a cada build. Procura o config em locais comuns.
GAPROMPT="$SKILL_DIR/make_ga_prompt.py"
GACFG=""
for c in "$PAPER/graphical_abstract.config.json" "$ROOT/graphical_abstract.config.json" \
         "$SRC/graphical_abstract.config.json"; do
  [ -f "$c" ] && { GACFG="$c"; break; }
done
if [ -n "$PY" ] && [ -n "$GACFG" ] && [ -f "$GAPROMPT" ]; then
  "$PY" "$GAPROMPT" "$GACFG" --out "$OUT" --docx "$OUT"/*.docx >/dev/null 2>&1 \
    && echo "== prompt graphical abstract (FigureLabs) inserido na 1a pagina dos docx ==" \
    || echo "== [aviso] prompt graphical abstract falhou =="
fi

# sincroniza SOMENTE a EN limpa (+figuras). NUNCA a PT marcada.
if [ -n "$SUBMIT" ]; then
  mkdir -p "$SUBMIT/figuras"
  cp -f "$OUT"/manuscript_EN_submission.* "$SUBMIT/" 2>/dev/null
  cp -f "$FIG"/*.png "$SUBMIT/figuras/" 2>/dev/null
  # prompt files (FigureLabs) tambem vao p/ a vitrine
  cp -f "$OUT"/*_GRAPHICAL_ABSTRACT_PROMPT.* "$SUBMIT/" 2>/dev/null
  echo "== sincronizado p/ submissão (apenas EN limpa): $SUBMIT =="
fi
