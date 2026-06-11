"""
lilo_pycharm_mcp.py — MCP Server LILO para PyCharm AI Assistant
================================================================
Servidor MCP unificado via API centralizada do lilo.py.
Todos os tools (SQL, PDF, Scholar, Prism, Villa Lobos, Gateway)
são registrados dinamicamente a partir do orquestrador.

Pré-requisito (uma vez):
    pip install mcp

Configurar no PyCharm:
  Settings → Tools → AI Assistant → Model Context Protocol (MCP)
  + Add server (Command)
    Name:               LILO
    Command:            python
    Arguments:          C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente\\lilo_pycharm_mcp.py
    Environment Vars:   PYTHONPATH=C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente
    Working directory:  C:\\Users\\luizd\\OneDrive\\Data_Science\\Projetos\\IA.agente
"""

import sys
import os
from pathlib import Path

# ── Setup paths ─────────────────────────────────────────────────────────────
LILO_ROOT = Path(__file__).parent
sys.path.insert(0, str(LILO_ROOT))
os.environ.setdefault("PYTHONPATH", str(LILO_ROOT))

# ── Verificar/instalar dependência mcp ──────────────────────────────────────
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    import subprocess
    sys.stderr.write("[LILO] Instalando pacote 'mcp'...\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "mcp>=1.0.0"])
    from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LILO")

# ── Lazy init ───────────────────────────────────────────────────────────────
_lilo_loaded = False

def _ensure_lilo():
    global _lilo_loaded
    if not _lilo_loaded:
        from shared.utils import load_env
        load_env()
        _lilo_loaded = True


# ═══════════════════════════════════════════════════════════════════════════
# Tools — todos delegam ao orquestrador centralizado lilo.py
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def lilo_chat(query: str, model: str = "") -> str:
    """
    Chat geral com LILO. Usa Ollama local ou Claude conforme complexidade.
    Args:
        query: Pergunta ou comando
        model: Modelo específico (opcional)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query}
    if model:
        args["model"] = model
    return handle_tool_call("lilo_chat", args)


@mcp.tool()
def lilo_sql(query: str, db_path: str = "", table: str = "") -> str:
    """
    Análise SQL: queries, estatísticas, ANOVA, t-test.
    Args:
        query: Pergunta sobre dados ou query SQL direta
        db_path: Caminho do banco SQLite (opcional)
        table: Nome da tabela (opcional)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query}
    if db_path: args["db_path"] = db_path
    if table: args["table"] = table
    return handle_tool_call("sql_query", args)


@mcp.tool()
def lilo_pdf(query: str, file_path: str = "", mode: str = "simple") -> str:
    """
    Sumariza ou analisa PDFs científicos.
    Args:
        query: O que fazer com o PDF
        file_path: Caminho do arquivo PDF
        mode: simple, introduction, methods, results
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": query, "mode": mode}
    if file_path: args["file_path"] = file_path
    return handle_tool_call("pdf_summarize", args)


@mcp.tool()
def lilo_scholar(query: str, max_results: int = 5) -> str:
    """
    Busca acadêmica PubMed + arXiv com síntese de literatura.
    Args:
        query: Tópico (ex: 'inibidores TcTR Trypanosoma')
        max_results: Máximo de resultados (padrão: 5)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("scholar_synthesize", {"query": query, "max_results": max_results})


@mcp.tool()
def lilo_health() -> str:
    """Verifica status de todos os subagentes LILO, Ollama e backends."""
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("lilo_health", {})


# ── Prism AI ────────────────────────────────────────────────────────────────

@mcp.tool()
def prism_analyze(file_path: str, output_dir: str = "", language: str = "en", alpha: float = 0.05) -> str:
    """
    Análise científica completa: detecta experimento, testa hipóteses,
    gera gráficos publicação e texto de Resultados. Aceita .xlsx e .csv.
    Args:
        file_path: Caminho para arquivo de dados (.xlsx ou .csv)
        output_dir: Diretório para salvar resultados (opcional)
        language: Idioma do texto (en/pt)
        alpha: Nível de significância (default: 0.05)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("prism_analyze", {
        "query": f"analyze {file_path}",
        "file_path": file_path, "output_dir": output_dir,
        "language": language, "alpha": alpha,
    })


@mcp.tool()
def prism_classify(file_path: str) -> str:
    """
    Classifica tipo de experimento a partir dos dados.
    Args:
        file_path: Caminho para arquivo de dados
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("prism_classify", {"query": f"classify {file_path}", "file_path": file_path})


@mcp.tool()
def prism_audit(file_path: str, claimed_test: str = "") -> str:
    """
    Audita análise estatística existente: detecta erros, sugere correções.
    Args:
        file_path: Caminho para arquivo de dados
        claimed_test: Teste estatístico usado (para auditoria)
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    args = {"query": f"audit {file_path}", "file_path": file_path}
    if claimed_test: args["claimed_test"] = claimed_test
    return handle_tool_call("prism_audit", args)


# ── Villa Lobos ─────────────────────────────────────────────────────────────

@mcp.tool()
def villa_pipeline(task: str, iterations: int = 1, use_reader: bool = True, base_path: str = ".") -> str:
    """
    Pipeline completo Villa Lobos (5 agentes):
    Orquestrador → Planejador → Leitor → Executor → Relator.
    Args:
        task: Tarefa a executar
        iterations: Iterações do Executor (padrão: 1)
        use_reader: Analisar arquivos do projeto (padrão: True)
        base_path: Caminho do projeto para o Reader
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("villa_pipeline", {
        "query": task, "iterations": iterations,
        "use_reader": use_reader, "base_path": base_path,
    })


@mcp.tool()
def villa_quick_ask(question: str, agent: str = "worker") -> str:
    """
    Pergunta rápida a um agente Villa Lobos (sem pipeline completo).
    Args:
        question: Pergunta ou prompt
        agent: orchestrator, planner, reader, worker, reporter
    """
    _ensure_lilo()
    from lilo import handle_tool_call
    return handle_tool_call("villa_quick_ask", {"query": question, "agent": agent})


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    mcp.run(transport="stdio")
