"""
config.py — Configuração central do ScholarAgent (env-driven).

Aponta para o LLM local do Lilo (Ollama em :11434, formato /api/generate).
Tudo pode ser sobrescrito por variável de ambiente.
"""
from __future__ import annotations
import os

# --- LLM local (Lilo / Ollama, formato Ollama /api/generate) ---
LLM_URL = os.environ.get("SCHOLAR_LLM_URL", "http://localhost:11434/api/generate")
LLM_MODEL = os.environ.get("SCHOLAR_LLM_MODEL", "llama3.1:8b-instruct-q8_0")

# --- Embeddings locais (sentence-transformers) ---
# Multilíngue PT/EN (~470MB, CPU-friendly). Alternativas: all-MiniLM-L6-v2 (leve, só EN),
# BAAI/bge-m3 (melhor qualidade, ~2GB). Trocar exige re-ingestão (muda a dimensão).
EMBED_MODEL = os.environ.get("SCHOLAR_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# --- Reranker (cross-encoder; ausência cai para triagem por tokens) ---
# Padrão: multilíngue leve (~470MB, CPU). Máxima qualidade: BAAI/bge-reranker-v2-m3 (~2.3GB).
RERANKER_MODEL = os.environ.get("SCHOLAR_RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

# --- Base vetorial (multilíngue, sem seção references). Caminho ABSOLUTO sob a raiz
# do Lilo (este pacote vive em <lilo>/scholaragent/), independente do CWD. ---
_LILO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAIN_DIR = os.environ.get("SCHOLAR_BRAIN_DIR", os.path.join(_LILO_ROOT, "data", "scholar_brain"))

# --- CrossRef polite pool ---
CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "")
