"""
Rotas da API - Operações de Arquivos
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.tools.file_operations import file_ops
from app.core.permissions import PermissionDenied
import structlog

logger = structlog.get_logger()
router = APIRouter()


class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileListRequest(BaseModel):
    path: str
    recursive: bool = False


class FileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


@router.post("/read", response_model=FileResponse)
async def read_file(request: FileReadRequest):
    """Lê conteúdo de um arquivo"""
    try:
        content = await file_ops.read_file(request.path)
        return FileResponse(
            success=True,
            message="Arquivo lido com sucesso",
            data={"content": content}
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Erro ao ler arquivo", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write", response_model=FileResponse)
async def write_file(request: FileWriteRequest):
    """Escreve conteúdo em um arquivo"""
    try:
        await file_ops.write_file(request.path, request.content)
        return FileResponse(
            success=True,
            message="Arquivo escrito com sucesso"
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Erro ao escrever arquivo", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list", response_model=FileResponse)
async def list_directory(request: FileListRequest):
    """Lista conteúdo de um diretório"""
    try:
        items = await file_ops.list_directory(request.path, request.recursive)
        return FileResponse(
            success=True,
            message=f"{len(items)} itens encontrados",
            data={"items": items}
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Erro ao listar diretório", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{path:path}", response_model=FileResponse)
async def delete_file(path: str):
    """Deleta um arquivo"""
    try:
        await file_ops.delete_file(path)
        return FileResponse(
            success=True,
            message="Arquivo deletado com sucesso"
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Erro ao deletar arquivo", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
