"""
Serviço de Memória - Interface com ChromaDB
Implementa RAG para contexto persistente
"""

from typing import List, Dict, Any, Optional
import structlog
import httpx
from datetime import datetime
import hashlib

from app.core.config import settings

logger = structlog.get_logger()


class MemoryService:
    """Serviço de memória de longo prazo com RAG"""

    def __init__(self):
        self.chroma_host = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
        self.collection_name = settings.CHROMA_COLLECTION
        self.client: Optional[httpx.AsyncClient] = None
        self.collection_id: Optional[str] = None

    async def initialize(self):
        """Inicializa conexão com ChromaDB"""
        self.client = httpx.AsyncClient(base_url=self.chroma_host, timeout=30.0)
        logger.info("Memory Service inicializado", host=self.chroma_host)

        # Criar/obter coleção
        await self._ensure_collection()

    async def shutdown(self):
        """Fecha conexão"""
        if self.client:
            await self.client.aclose()

    async def _ensure_collection(self):
        """Garante que coleção existe"""
        try:
            # Tentar obter coleção
            response = await self.client.get(f"/api/v1/collections/{self.collection_name}")

            if response.status_code == 200:
                self.collection_id = response.json()["id"]
                logger.info("Coleção encontrada", name=self.collection_name)
            else:
                # Criar coleção
                await self._create_collection()

        except Exception as e:
            logger.warning("Erro ao verificar coleção, tentando criar", error=str(e))
            await self._create_collection()

    async def _create_collection(self):
        """Cria nova coleção"""
        try:
            payload = {
                "name": self.collection_name,
                "metadata": {"created_at": datetime.utcnow().isoformat()}
            }

            response = await self.client.post("/api/v1/collections", json=payload)
            response.raise_for_status()

            self.collection_id = response.json()["id"]
            logger.info("Coleção criada", name=self.collection_name)

        except Exception as e:
            logger.error("Erro ao criar coleção", error=str(e))
            raise

    async def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Adiciona entrada na memória

        Args:
            content: Conteúdo a armazenar
            metadata: Metadados adicionais
            embedding: Embedding pré-calculado (opcional)

        Returns:
            ID da entrada
        """
        # Gerar ID único
        doc_id = hashlib.sha256(
            f"{content}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        # Preparar metadados
        meta = metadata or {}
        meta["timestamp"] = datetime.utcnow().isoformat()

        payload = {
            "ids": [doc_id],
            "documents": [content],
            "metadatas": [meta]
        }

        if embedding:
            payload["embeddings"] = [embedding]

        try:
            response = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/add",
                json=payload
            )
            response.raise_for_status()

            logger.info("Memória adicionada", id=doc_id)
            return doc_id

        except Exception as e:
            logger.error("Erro ao adicionar memória", error=str(e))
            raise

    async def search_relevant(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Busca memórias relevantes usando similaridade semântica

        Args:
            query: Consulta de busca
            limit: Número máximo de resultados
            filter_metadata: Filtros de metadados

        Returns:
            Lista de conteúdos relevantes
        """
        payload = {
            "query_texts": [query],
            "n_results": limit
        }

        if filter_metadata:
            payload["where"] = filter_metadata

        try:
            response = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/query",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            documents = result.get("documents", [[]])[0]

            logger.info("Memórias encontradas", query=query[:50], count=len(documents))
            return documents

        except Exception as e:
            logger.error("Erro ao buscar memórias", error=str(e))
            return []

    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém memórias recentes

        Args:
            limit: Número de memórias

        Returns:
            Lista de memórias com metadados
        """
        try:
            response = await self.client.get(
                f"/api/v1/collections/{self.collection_name}/get",
                params={"limit": limit}
            )
            response.raise_for_status()

            result = response.json()

            memories = []
            for i in range(len(result.get("ids", []))):
                memories.append({
                    "id": result["ids"][i],
                    "content": result["documents"][i],
                    "metadata": result["metadatas"][i]
                })

            logger.info("Memórias recentes obtidas", count=len(memories))
            return memories

        except Exception as e:
            logger.error("Erro ao obter memórias recentes", error=str(e))
            return []

    async def clear_all(self):
        """Limpa todas as memórias (usar com cuidado!)"""
        try:
            # Deletar e recriar coleção
            await self.client.delete(f"/api/v1/collections/{self.collection_name}")
            await self._create_collection()

            logger.warning("Todas as memórias foram limpas")

        except Exception as e:
            logger.error("Erro ao limpar memórias", error=str(e))
            raise
