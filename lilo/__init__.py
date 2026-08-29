"""LILO v13 — agente de terminal 100% local sobre Ollama.

Um binario (`lilo`), um loop agentico com tool-calling nativo e as tools
(ler/ler_pdf/escrever/editar/listar/buscar/shell/memoria/mcp) atras de um
unico choke-point com portao de permissoes. Nada de dashboards, APIs ou subagentes de dominio no
nucleo — funcionalidade nova entra como TOOL atras do loop.
"""

__version__ = "13.12.0"
