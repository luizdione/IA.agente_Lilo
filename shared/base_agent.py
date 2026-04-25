"""
shared/base_agent.py — Interface padronizada para todos os subagentes LILO.

Todos os subagentes (SQL, PDF, Scholar, Gateway) herdam BaseAgent e
implementam run() e get_tools(). O orquestrador lilo.py usa essa interface
para roteamento e registro MCP.

Uso:
    from shared.base_agent import BaseAgent

    class MeuAgente(BaseAgent):
        name = "meu_agente"
        description = "Faz X e Y."

        def run(self, query: str, context: dict = {}) -> str:
            return "resposta"

        def get_tools(self) -> list:
            return [
                {
                    "name": "meu_agente_query",
                    "description": "Executa consulta no MeuAgente.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                }
            ]
"""

from abc import ABC, abstractmethod
from typing import Any
from .logger import get_logger


class BaseAgent(ABC):
    """
    Interface base para todos os subagentes LILO.

    Atributos de classe obrigatórios:
        name        — identificador único (ex: "sql", "pdf", "scholar")
        description — descrição usada pelo orquestrador para roteamento
    """

    name: str = "base"
    description: str = "Agente base LILO."

    def __init__(self):
        self.log = get_logger(self.__class__.__name__)
        self.log.info(f"Subagente '{self.name}' inicializado.")

    # ── Interface obrigatória ────────────────────────────────────────────────

    @abstractmethod
    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        """
        Processa uma query e retorna resposta em string.

        Args:
            query   — pergunta ou comando do usuário
            context — contexto adicional (arquivo, tab_name, histórico, etc.)

        Returns:
            Resposta em texto plano ou Markdown.
        """
        raise NotImplementedError

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """
        Retorna lista de tool-definitions no formato MCP (Model Context Protocol).

        Cada tool deve ter:
            name        — string única (ex: "sql_query")
            description — string descrevendo o que a tool faz
            inputSchema — JSON Schema dos argumentos aceitos

        Returns:
            Lista de dicts compatíveis com MCP tools/list.
        """
        raise NotImplementedError

    # ── Helpers opcionais ────────────────────────────────────────────────────

    def health(self) -> dict:
        """Retorna status básico do subagente. Subclasses podem sobrescrever."""
        return {"agent": self.name, "status": "ok"}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
