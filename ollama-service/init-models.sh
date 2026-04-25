#!/bin/sh
# init-models.sh — Aguarda Ollama iniciar e puxa os modelos configurados
set -e

echo "[LILO] Aguardando Ollama inicializar..."
MAX_WAIT=120
WAITED=0
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
  WAITED=$((WAITED + 2))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "[LILO] Timeout esperando Ollama ($MAX_WAIT s). Continuando sem pull."
    exit 0
  fi
done

echo "[LILO] Ollama pronto. Puxando modelos..."

# Modelo principal de chat
ollama pull llama3.1:8b-instruct-q8_0 || echo "WARN: falha ao puxar llama3.1:8b"

# Modelo de código
ollama pull qwen2.5-coder:14b || echo "WARN: falha ao puxar qwen2.5-coder:14b"

# Modelo de embeddings
ollama pull mxbai-embed-large:latest || echo "WARN: falha ao puxar mxbai-embed-large"

echo "[LILO] Modelos carregados com sucesso."
