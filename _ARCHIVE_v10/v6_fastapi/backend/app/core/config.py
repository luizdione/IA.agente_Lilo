"""
Configuração centralizada do backend
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Versão
    VERSION: str = "6.0.0"

    # Modo debug
    DEBUG: bool = False

    # Ollama
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL_PLANNER: str = "phi3:14b-medium-128k-instruct-q4_K_M"
    OLLAMA_MODEL_EXECUTOR: str = "qwen2.5-coder:14b"
    OLLAMA_MODEL_CRITIC: str = "phi3:14b-medium-128k-instruct-q4_K_M"
    OLLAMA_MODEL_CHAT: str = "llama3.1:8b-instruct-q8_0"
    OLLAMA_MODEL_EMBEDDINGS: str = "mxbai-embed-large"

    # Chroma (banco vetorial)
    CHROMA_HOST: str = "memory"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "lilo_memory"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000"]

    # Diretórios
    WORKSPACE_DIR: str = "/workspace"
    SANDBOX_DIR: str = "/workspace/sandbox"
    LOGS_DIR: str = "/app/logs"

    # Permissões de arquivo
    ALLOWED_EXTENSIONS: List[str] = [
        ".py", ".txt", ".md", ".json", ".yaml", ".yml",
        ".csv", ".tsv", ".xml", ".html", ".css", ".js",
        ".sh", ".bash", ".r", ".R", ".fasta", ".fastq",
        ".fq", ".sam", ".bam", ".vcf", ".gff", ".gtf"
    ]

    FORBIDDEN_PATHS: List[str] = [
        "/etc", "/sys", "/proc", "/dev", "/root"
    ]

    # Limites de recursos
    MAX_FILE_SIZE_MB: int = 100
    MAX_EXECUTION_TIME_SECONDS: int = 300
    MAX_MEMORY_MB: int = 2048

    # Auditoria
    ENABLE_AUDIT_LOG: bool = True
    AUDIT_LOG_FILE: str = "/app/logs/audit.jsonl"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
