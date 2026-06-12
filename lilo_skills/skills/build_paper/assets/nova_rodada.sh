#!/usr/bin/env bash
# nova_rodada.sh <RAIZ_DO_PROJETO> "<foco da rodada>"
# Arquiva as versões atuais em OBSOLETOS/paper_rodadaN_<data>/ e adiciona um
# esqueleto de entrada no PAPER/LOG_VERSOES.md. Rode ANTES de gerar a nova
# versão (depois edite o log com o que de fato mudou).
set -u
ROOT="${1:?uso: nova_rodada.sh <RAIZ_DO_PROJETO> \"<foco>\"}"
FOCO="${2:-(definir)}"
PAPER="$ROOT/PAPER"; OUT="$PAPER/build"; OBS="$ROOT/OBSOLETOS"; LOG="$PAPER/LOG_VERSOES.md"
DATA="$(date +%Y-%m-%d)"

# número da próxima rodada = (rodadas já registradas no log) + 1
N=0
[ -f "$LOG" ] && N="$(grep -c '^## Rodada ' "$LOG" 2>/dev/null || echo 0)"
PREV=$((N))            # a rodada que está sendo arquivada
DEST="$OBS/paper_rodada${PREV}_${DATA}"

mkdir -p "$DEST"
if ls "$OUT"/*.docx "$OUT"/*.tex "$OUT"/*.pdf >/dev/null 2>&1; then
  cp -f "$OUT"/*.docx "$OUT"/*.tex "$OUT"/*.pdf "$DEST/" 2>/dev/null
  echo "Arquivado build atual em: $DEST"
else
  echo "Nada em $OUT para arquivar (primeira rodada?)."
fi

# entrada no log (esqueleto p/ você completar)
{
  echo ""
  echo "## Rodada $((N+1)) — $DATA (foco: $FOCO)"
  echo "- [o que mudou e por quê: decisões, dados/refs incorporados]."
  echo "- [nº de arquivos regenerados; nº de páginas dos PDFs]."
  echo "- **Pendências:** [o que ficou para a próxima rodada]."
} >> "$LOG"
echo "Entrada de log adicionada em: $LOG (Rodada $((N+1)))"
echo "Agora: regenere figuras (se preciso) e rode build.sh; depois edite o log."
