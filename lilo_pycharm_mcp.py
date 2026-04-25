"""
lilo_pycharm_mcp.py — MCP Server LILO para PyCharm AI Assistant
================================================================
Servidor MCP unificado: subagentes LILO + pipeline Villa Lobos.

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

Ferramentas (7):
  lilo_chat, lilo_sql, lilo_pdf, lilo_scholar, lilo_health,
  villa_pipeline, villa_quick_ask
"""

import sys
import os
from pathlib import Path

# ── Setup paths ─────────────────────────────────────────────────────────────
LILO_ROOT = Path(__file__).parent
VILLA_ROOT = LILO_ROOT.parent / "osquestrador_ollama" / "villa_lobos"

sys.path.insert(0, str(LILO_ROOT))
if VILLA_ROOT.exists():
    sys.path.insert(0, str(VILLA_ROOT))

# Garantir que .env seja carregado
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
# LILO Tools
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
    from lilo import route
    ctx = {"model": model} if model else {}
    return route(query, tab="gateway", context=ctx)


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
    from lilo import route
    ctx = {}
    if db_path: ctx["db_path"] = db_path
    if table: ctx["table"] = table
    return route(query, tab="sql", context=ctx)


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
    from lilo import route
    ctx = {"mode": mode}
    if file_path: ctx["file_path"] = file_path
    return route(query, tab="pdf", context=ctx)


@mcp.tool()
def lilo_scholar(query: str, max_results: int = 5) -> str:
    """
    Busca acadêmica PubMed + arXiv com síntese de literatura.
    Args:
        query: Tópico (ex: 'inibidores TcTR Trypanosoma')
        max_results: Máximo de resultados (padrão: 5)
    """
    _ensure_lilo()
    from lilo import route
    return route(query, tab="scholar", context={"max_results": max_results, "synthesize": True})


@mcp.tool()
def lilo_health() -> str:
    """Verifica status de todos os subagentes LILO, Ollama e backends."""
    _ensure_lilo()
    from lilo import health_check
    return health_check()


# ═══════════════════════════════════════════════════════════════════════════
# Villa Lobos Tools
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def villa_pipeline(
    task: str,
    iterations: int = 1,
    use_reader: bool = True,
    base_path: str = ".",
) -> str:
    """
    Pipeline completo Villa Lobos (5 agentes):
    Orquestrador → Planejador → Leitor → Executor → Relator.
    Salva resultado no Obsidian.
    Args:
        task: Tarefa a executar
        iterations: Iterações do Executor (padrão: 1)
        use_reader: Analisar arquivos do projeto (padrão: True)
        base_path: Caminho do projeto para o Reader
    """
    try:
        from main import run_pipeline as _run
        result = _run(task=task, iterations=iterations, use_reader=use_reader,
                       base_path=base_path, verbose=False)
        lines = [
            f"## Tarefa: {result['task']}",
            f"**Status**: {result['status']} | **Duração**: {result['duration_s']:.1f}s",
            "", "### Plano", result.get("plan", "-")[:800],
            "", "### Resultado", result.get("result", "-")[:1200],
            "", "### Relatório", result.get("report", "-")[:600],
        ]
        return "\n".join(lines)
    except ImportError:
        return "[Villa Lobos não disponível] pip install mcp && verifique osquestrador_ollama no path."
    except Exception as e:
        return f"[ERRO] {type(e).__name__}: {e}"


@mcp.tool()
def villa_quick_ask(question: str, agent: str = "worker") -> str:
    """
    Pergunta rápida a um agente Villa Lobos (sem pipeline completo).
    Args:
        question: Pergunta ou prompt
        agent: orchestrator, planner, reader, worker, reporter
    """
    try:
        villa_config = __import__("config")
        from ollama_client import generate, is_online
        if not is_online():
            return "[ERRO] Ollama não está rodando. Execute: ollama serve"
        model = villa_config.MODELS.get(agent, villa_config.MODELS["worker"])
        response = generate(model=model, prompt=question)
        return f"**[{agent.upper()} / {model}]**\n\n{response}"
    except ImportError:
        return "[Villa Lobos não disponível]"
    except Exception as e:
        return f"[ERRO] {type(e).__name__}: {e}"


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    mcp.run(transport="stdio")
