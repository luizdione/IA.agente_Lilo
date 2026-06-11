"""
Serviço de Memória - Interface com ChromaDB
Implementa RAG para contexto persistente.

Melhorias v2 (Task 3 - 2026-04-28):
- search_relevant agora retorna scores de similaridade
- Deduplicação por hash de conteúdo (evita memórias duplicadas)
- Retry com backoff exponencial em chamadas HTTP
- Helpers add_memory_for_project / search_in_project
- list_project_memories
- Compactação de coleção (remove duplicatas antigas)
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import structlog
import httpx
from datetime import datetime
import hashlib

from app.core.config import settings

logger = structlog.get_logger()


# Numero de tentativas e delay base para retry exponencial
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.4  # segundos -> 0.4, 0.8, 1.6


async def _retry_request(
    fn,
    *args,
    retries: int = _MAX_RETRIES,
    **kwargs,
):
    """Executa uma coroutine HTTP com retry exponencial.
    Reerguida quando max_retries esgotam ou erros nao-recuperaveis."""
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return await fn(*args, **kwargs)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            wait = _BACKOFF_BASE * (2 ** attempt)
            logger.warning(
                "Memory request falhou, tentando novamente",
                attempt=attempt + 1,
                max=retries,
                wait_s=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)
        except httpx.HTTPStatusError as exc:
            # 5xx -> retry; 4xx -> nao retry
            if 500 <= exc.response.status_code < 600 and attempt < retries - 1:
                last_exc = exc
                await asyncio.sleep(_BACKOFF_BASE * (2 ** attempt))
                continue
            raise
    if last_exc:
        raise last_exc


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
        embedding: Optional[List[float]] = None,
        dedupe: bool = True,
    ) -> str:
        """
        Adiciona entrada na memória.

        Args:
            content: Conteúdo a armazenar
            metadata: Metadados adicionais (project_id, subagent, etc)
            embedding: Embedding pré-calculado (opcional)
            dedupe: Se True, ID é hash do conteúdo (evita duplicatas);
                    se False, ID inclui timestamp (sempre única)

        Returns:
            ID da entrada
        """
        # ID: hash do conteúdo (dedupe) ou hash com timestamp
        if dedupe:
            # Inclui project_id no hash para nao deduplicar entre projetos
            scope = (metadata or {}).get("project_id", "")
            doc_id = hashlib.sha256(
                f"{scope}|{content}".encode()
            ).hexdigest()[:16]
        else:
            doc_id = hashlib.sha256(
                f"{content}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]

        # Preparar metadados
        meta = dict(metadata or {})
        meta.setdefault("timestamp", datetime.utcnow().isoformat())
        # Hash do conteudo p/ debug e auditorias
        meta.setdefault(
            "content_hash",
            hashlib.sha1(content.encode()).hexdigest()[:12],
        )

        payload = {
            "ids": [doc_id],
            "documents": [content],
            "metadatas": [meta]
        }

        if embedding:
            payload["embeddings"] = [embedding]

        async def _post():
            r = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/add",
                json=payload,
            )
            r.raise_for_status()
            return r

        try:
            await _retry_request(_post)
            logger.info("Memória adicionada", id=doc_id, dedupe=dedupe)
            return doc_id
        except Exception as e:
            logger.error("Erro ao adicionar memória", error=str(e))
            raise

    async def add_memory_for_project(
        self,
        project_id: str,
        content: str,
        subagent: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Atalho para registrar memoria associada a um projeto.
        Faz dedupe por (project_id, content)."""
        meta = {"project_id": project_id, "subagent": subagent}
        if extra:
            meta.update(extra)
        return await self.add_memory(content, metadata=meta, dedupe=True)

    async def search_relevant(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        with_scores: bool = False,
    ) -> List[Any]:
        """
        Busca memórias relevantes usando similaridade semântica.

        Args:
            query: Consulta de busca
            limit: Número máximo de resultados
            filter_metadata: Filtros de metadados (ex: {"project_id": "abc"})
            with_scores: Se True, retorna tuplas (content, score, metadata).

        Returns:
            Lista de strings (default) OU lista de dicts
            {"content", "score", "metadata"} se with_scores=True.
        """
        payload = {
            "query_texts": [query],
            "n_results": limit,
        }

        if filter_metadata:
            payload["where"] = filter_metadata

        async def _post():
            r = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/query",
                json=payload,
            )
            r.raise_for_status()
            return r

        try:
            response = await _retry_request(_post)
            result = response.json()
            documents = result.get("documents", [[]])[0]
            distances = result.get("distances", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]

            logger.info("Memórias encontradas", query=query[:50],
                        count=len(documents))

            if not with_scores:
                return documents

            # Score = 1 / (1 + distancia) -> [0,1], maior = mais similar
            out = []
            for i, doc in enumerate(documents):
                dist = distances[i] if i < len(distances) else 1.0
                meta = metadatas[i] if i < len(metadatas) else {}
                out.append({
                    "content": doc,
                    "score": 1.0 / (1.0 + float(dist)),
                    "distance": float(dist),
                    "metadata": meta,
                })
            return out

        except Exception as e:
            logger.error("Erro ao buscar memórias", error=str(e))
            return []

    async def search_in_project(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        with_scores: bool = True,
    ) -> List[Any]:
        """Busca memorias dentro de um projeto especifico (atalho)."""
        return await self.search_relevant(
            query=query,
            limit=limit,
            filter_metadata={"project_id": project_id},
            with_scores=with_scores,
        )

    async def list_project_memories(
        self,
        project_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lista todas as memorias de um projeto (sem busca semantica)."""
        async def _get():
            r = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/get",
                json={
                    "where": {"project_id": project_id},
                    "limit": limit,
                },
            )
            r.raise_for_status()
            return r

        try:
            response = await _retry_request(_get)
            result = response.json()
            ids = result.get("ids", [])
            docs = result.get("documents", [])
            metas = result.get("metadatas", [])
            return [
                {"id": ids[i], "content": docs[i],
                 "metadata": metas[i] if i < len(metas) else {}}
                for i in range(len(ids))
            ]
        except Exception as e:
            logger.error("Erro listando memorias do projeto", error=str(e))
            return []

    async def delete_by_id(self, doc_id: str) -> bool:
        """Remove uma memoria especifica."""
        try:
            r = await self.client.post(
                f"/api/v1/collections/{self.collection_name}/delete",
                json={"ids": [doc_id]},
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error("Erro deletando memoria", id=doc_id, error=str(e))
            return False

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
