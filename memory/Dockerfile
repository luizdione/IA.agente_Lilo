FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# ChromaDB com numpy compatível
RUN pip install --no-cache-dir "chromadb>=0.5.0,<0.6.0" "numpy<2.0"

RUN mkdir -p /data

EXPOSE 8001

# ChromaDB >= 0.5 usa `chroma run`
CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8001", "--path", "/data"]
