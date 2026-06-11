"""
Ferramentas de Operação de Arquivos
Todas as operações passam pelo sistema de permissões e são auditadas
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog
import aiofiles
import json
from datetime import datetime

from app.core.permissions import permission_manager, PermissionLevel, PermissionDenied
from app.core.config import settings

logger = structlog.get_logger()


class AuditLogger:
    """Logger de auditoria para todas as operações de arquivo"""

    def __init__(self):
        self._audit_file = None

    @property
    def audit_file(self) -> Path:
        if self._audit_file is None:
            self._audit_file = Path(settings.AUDIT_LOG_FILE)
            try:
                parent = self._audit_file.parent
                if parent.parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Não foi possível criar dir de auditoria: {e}")
        return self._audit_file

    async def log(self, operation: str, path: str, user: str = "agent",
                  metadata: Optional[Dict[str, Any]] = None, success: bool = True):
        """Registra operação no log de auditoria"""
        if not settings.ENABLE_AUDIT_LOG:
            return

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "path": path,
            "user": user,
            "success": success,
            "metadata": metadata or {}
        }

        try:
            async with aiofiles.open(self.audit_file, mode='a') as f:
                await f.write(json.dumps(entry) + '\n')
        except (PermissionError, OSError) as e:
            logger.warning(f"Falha ao escrever audit log: {e}")


audit_logger = AuditLogger()


class FileOperations:
    """Operações de arquivo com permissões e auditoria"""

    @staticmethod
    async def read_file(path: str) -> str:
        """
        Lê conteúdo de um arquivo

        Args:
            path: Caminho do arquivo

        Returns:
            Conteúdo do arquivo

        Raises:
            PermissionDenied: Se acesso negado
            FileNotFoundError: Se arquivo não existe
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.READ)

        try:
            async with aiofiles.open(validated_path, mode='r', encoding='utf-8') as f:
                content = await f.read()

            await audit_logger.log("read", str(validated_path))
            logger.info("Arquivo lido", path=str(validated_path), size=len(content))
            return content

        except Exception as e:
            await audit_logger.log("read", str(validated_path), success=False, metadata={"error": str(e)})
            raise

    @staticmethod
    async def write_file(path: str, content: str, create_dirs: bool = True) -> bool:
        """
        Escreve conteúdo em um arquivo

        Args:
            path: Caminho do arquivo
            content: Conteúdo a escrever
            create_dirs: Criar diretórios pais se não existirem

        Returns:
            True se sucesso

        Raises:
            PermissionDenied: Se acesso negado
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.WRITE)

        try:
            if create_dirs:
                validated_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(validated_path, mode='w', encoding='utf-8') as f:
                await f.write(content)

            await audit_logger.log("write", str(validated_path), metadata={"size": len(content)})
            logger.info("Arquivo escrito", path=str(validated_path), size=len(content))
            return True

        except Exception as e:
            await audit_logger.log("write", str(validated_path), success=False, metadata={"error": str(e)})
            raise

    @staticmethod
    async def create_file(path: str, content: str = "") -> bool:
        """
        Cria um novo arquivo

        Args:
            path: Caminho do arquivo
            content: Conteúdo inicial (opcional)

        Returns:
            True se sucesso

        Raises:
            PermissionDenied: Se acesso negado
            FileExistsError: Se arquivo já existe
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.WRITE)

        if validated_path.exists():
            raise FileExistsError(f"Arquivo {validated_path} já existe")

        return await FileOperations.write_file(str(validated_path), content)

    @staticmethod
    async def delete_file(path: str) -> bool:
        """
        Deleta um arquivo

        Args:
            path: Caminho do arquivo

        Returns:
            True se sucesso

        Raises:
            PermissionDenied: Se acesso negado
            FileNotFoundError: Se arquivo não existe
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.DELETE)

        try:
            validated_path.unlink()

            await audit_logger.log("delete", str(validated_path))
            logger.info("Arquivo deletado", path=str(validated_path))
            return True

        except Exception as e:
            await audit_logger.log("delete", str(validated_path), success=False, metadata={"error": str(e)})
            raise

    @staticmethod
    async def list_directory(path: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Lista conteúdo de um diretório

        Args:
            path: Caminho do diretório
            recursive: Listar recursivamente

        Returns:
            Lista de arquivos/diretórios com metadados

        Raises:
            PermissionDenied: Se acesso negado
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.READ)

        if not validated_path.is_dir():
            raise NotADirectoryError(f"{validated_path} não é um diretório")

        results = []

        if recursive:
            items = validated_path.rglob("*")
        else:
            items = validated_path.iterdir()

        for item in items:
            try:
                # Verificar permissão para cada item
                permission_manager.validate_path(item)

                stat = item.stat()
                results.append({
                    "path": str(item.relative_to(validated_path.parent)),
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except PermissionDenied:
                # Pular itens sem permissão
                continue

        await audit_logger.log("list", str(validated_path), metadata={"count": len(results)})
        logger.info("Diretório listado", path=str(validated_path), items=len(results))

        return results

    @staticmethod
    async def create_directory(path: str) -> bool:
        """
        Cria um diretório

        Args:
            path: Caminho do diretório

        Returns:
            True se sucesso

        Raises:
            PermissionDenied: Se acesso negado
        """
        validated_path = permission_manager.require_permission(path, PermissionLevel.WRITE)

        try:
            validated_path.mkdir(parents=True, exist_ok=True)

            await audit_logger.log("mkdir", str(validated_path))
            logger.info("Diretório criado", path=str(validated_path))
            return True

        except Exception as e:
            await audit_logger.log("mkdir", str(validated_path), success=False, metadata={"error": str(e)})
            raise

    @staticmethod
    async def move_file(source: str, destination: str) -> bool:
        """
        Move/renomeia um arquivo

        Args:
            source: Caminho de origem
            destination: Caminho de destino

        Returns:
            True se sucesso
        """
        src_path = permission_manager.require_permission(source, PermissionLevel.DELETE)
        dst_path = permission_manager.require_permission(destination, PermissionLevel.WRITE)

        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dst_path)

            await audit_logger.log("move", str(src_path), metadata={"destination": str(dst_path)})
            logger.info("Arquivo movido", source=str(src_path), destination=str(dst_path))
            return True

        except Exception as e:
            await audit_logger.log("move", str(src_path), success=False, metadata={"error": str(e)})
            raise


# Singleton
file_ops = FileOperations()
