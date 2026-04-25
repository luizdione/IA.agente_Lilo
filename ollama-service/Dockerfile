FROM ollama/ollama:latest

# Expor porta padrão do Ollama
EXPOSE 11434

# Script de inicialização para puxar modelos
COPY init-models.sh /init-models.sh
RUN chmod +x /init-models.sh

# Comando de inicialização
CMD ["/bin/sh", "-c", "ollama serve & /init-models.sh && wait"]
