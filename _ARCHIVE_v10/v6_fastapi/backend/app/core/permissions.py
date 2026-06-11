"""
Sistema de Permissões e Sandboxing
Garante que todas as operações de arquivo são seguras e autorizadas
"""

from pathlib import Path
from typing import Tuple, Optional
import structlog
from enum import Enum

from app.core.config import settings

logger = structlog.get_logger()


class PermissionLevel(str, Enum):
    """Níveis de permissão"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


class PermissionDenied(Exception):
    """Exceção de permissão negada"""
    pass


class FilePermissionManager:
    """Gerenciador de permissões de arquivo"""

    def __init__(self):
        self.workspace = Path(settings.WORKSPACE_DIR).resolve()
        self.sandbox = Path(settings.SANDBOX_DIR).resolve()
        self.allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        self.forbidden_paths = [Path(p) for p in settings.FORBIDDEN_PATHS]

    def validate_path(self, file_path: str | Path) -> Path:
        """
        Valida se um caminho é seguro para acesso

        Args:
            file_path: Caminho do arquivo

        Returns:
            Path absoluto validado

        Raises:
            PermissionDenied: Se o caminho não é permitido
        """
        path = Path(file_path).resolve()

        # 1. Verificar se está dentro do workspace
        try:
            path.relative_to(self.workspace)
        except ValueError:
            logger.warning("Acesso negado: fora do workspace", path=str(path))
            raise PermissionDenied(f"Acesso negado: {path} está fora do workspace permitido")

        # 2. Verificar caminhos proibidos
        for forbidden in self.forbidden_paths:
            if path.is_relative_to(forbidden):
                logger.warning("Acesso negado: caminho proibido", path=str(path))
                raise PermissionDenied(f"Acesso negado: {path} está em área proibida")

        # 3. Verificar extensão (apenas para arquivos existentes ou com extensão)
        if path.suffix and path.suffix not in self.allowed_extensions:
            logger.warning("Acesso negado: extensão não permitida", path=str(path), ext=path.suffix)
            raise PermissionDenied(f"Extensão {path.suffix} não permitida")

        return path

    def check_permission(self, file_path: str | Path, permission: PermissionLevel) -> bool:
        """
        Verifica se uma operação é permitida

        Args:
            file_path: Caminho do arquivo
            permission: Nível de permissão necessário

        Returns:
            True se permitido, False caso contrário
        """
        try:
            path = self.validate_path(file_path)

            # Verificar tamanho de arquivo para operações de escrita
            if permission in [PermissionLevel.WRITE, PermissionLevel.EXECUTE]:
                if path.exists():
                    size_mb = path.stat().st_size / (1024 * 1024)
                    if size_mb > settings.MAX_FILE_SIZE_MB:
                        logger.warning("Arquivo muito grande", path=str(path), size_mb=size_mb)
                        return False

            return True

        except PermissionDenied:
            return False

    def require_permission(self, file_path: str | Path, permission: PermissionLevel) -> Path:
        """
        Requer permissão ou levanta exceção

        Args:
            file_path: Caminho do arquivo
            permission: Nível de permissão necessário

        Returns:
            Path validado

        Raises:
            PermissionDenied: Se permissão negada
        """
        path = self.validate_path(file_path)

        if not self.check_permission(path, permission):
            raise PermissionDenied(f"Permissão {permission} negada para {path}")

        logger.info("Permissão concedida", path=str(path), permission=permission.value)
        return path


# Instância global
permission_manager = FilePermissionManager()
