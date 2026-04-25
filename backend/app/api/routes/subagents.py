"""
Rotas da API - Sub-Agentes Especializados
Integra PDF Scholar, SQL Analysis e outros sub-agentes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import structlog
from pathlib import Path
import tempfile
import shutil

from app.services.model_manager import get_model_manager
from app.services.subagents.pdf_scholar_agent import PDFScholarAgent
from app.services.subagents.sql_analysis_agent import SQLAnalysisAgent

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class PDFAnalysisRequest(BaseModel):
    pdf_path: str
    mode: str = "simple"  # simple, introduction, methods


class PDFBatchRequest(BaseModel):
    pdf_dir: str
    mode: str = "simple"


class SQLAnalysisRequest(BaseModel):
    connection_string: str
    query: str
    analysis_type: str = "descriptive"  # descriptive, statistical, comparative


class SQLGenerateRequest(BaseModel):
    table_schema: Dict[str, Any]
    natural_query: str


class SQLExplainRequest(BaseModel):
    query: str


class AnalysisResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None


# ============================================================================
# PDF Scholar Agent Endpoints
# ============================================================================

@router.post("/pdf/analyze", response_model=AnalysisResponse)
async def analyze_pdf(request: PDFAnalysisRequest):
    """
    Analisa PDF científico

    - **pdf_path**: Caminho do PDF (relativo a /workspace)
    - **mode**: Modo de análise (simple, introduction, methods)
    """
    logger.info("API: Analisar PDF", path=request.pdf_path, mode=request.mode)

    try:
        model_manager = get_model_manager()
        agent = PDFScholarAgent(model_manager)

        # Resolver caminho
        workspace = Path("/workspace")
        pdf_path = workspace / request.pdf_path

        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF não encontrado: {request.pdf_path}")

        result = await agent.analyze_pdf(str(pdf_path), request.mode)

        return AnalysisResponse(
            success=True,
            data=result
        )

    except Exception as e:
        logger.error("Erro ao analisar PDF", error=str(e))
        return AnalysisResponse(
            success=False,
            data=None,
            error=str(e)
        )


@router.post("/pdf/upload-analyze")
async def upload_and_analyze_pdf(
    file: UploadFile = File(...),
    mode: str = "simple"
):
    """
    Upload e análise de PDF

    - **file**: Arquivo PDF
    - **mode**: Modo de análise
    """
    logger.info("API: Upload e análise de PDF", filename=file.filename, mode=mode)

    # Validar extensão
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos")

    try:
        # Salvar temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Analisar
        model_manager = get_model_manager()
        agent = PDFScholarAgent(model_manager)

        result = await agent.analyze_pdf(tmp_path, mode)

        # Remover temp file
        Path(tmp_path).unlink()

        return AnalysisResponse(
            success=True,
            data=result
        )

    except Exception as e:
        logger.error("Erro ao processar upload", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/batch", response_model=AnalysisResponse)
async def batch_analyze_pdfs(request: PDFBatchRequest):
    """
    Análise em lote de PDFs

    - **pdf_dir**: Diretório com PDFs (relativo a /workspace)
    - **mode**: Modo de análise
    """
    logger.info("API: Análise em lote", dir=request.pdf_dir, mode=request.mode)

    try:
        model_manager = get_model_manager()
        agent = PDFScholarAgent(model_manager)

        # Resolver caminho
        workspace = Path("/workspace")
        pdf_dir = workspace / request.pdf_dir

        if not pdf_dir.exists():
            raise HTTPException(status_code=404, detail=f"Diretório não encontrado: {request.pdf_dir}")

        results = await agent.batch_analyze(str(pdf_dir), request.mode)

        return AnalysisResponse(
            success=True,
            data={"results": results, "count": len(results)}
        )

    except Exception as e:
        logger.error("Erro em análise em lote", error=str(e))
        return AnalysisResponse(
            success=False,
            data=None,
            error=str(e)
        )


# ============================================================================
# SQL Analysis Agent Endpoints
# ============================================================================

@router.post("/sql/analyze", response_model=AnalysisResponse)
async def analyze_sql_data(request: SQLAnalysisRequest):
    """
    Analisa dados de banco SQL

    - **connection_string**: String de conexão (ex: mysql://user:pass@host/db)
    - **query**: Query SQL
    - **analysis_type**: Tipo de análise (descriptive, statistical, comparative)
    """
    logger.info("API: Análise SQL", type=request.analysis_type)

    try:
        model_manager = get_model_manager()
        agent = SQLAnalysisAgent(model_manager)

        result = await agent.analyze_data(
            request.connection_string,
            request.query,
            request.analysis_type
        )

        return AnalysisResponse(
            success=True,
            data=result
        )

    except Exception as e:
        logger.error("Erro ao analisar dados SQL", error=str(e))
        return AnalysisResponse(
            success=False,
            data=None,
            error=str(e)
        )


@router.post("/sql/generate", response_model=AnalysisResponse)
async def generate_sql(request: SQLGenerateRequest):
    """
    Gera SQL a partir de linguagem natural

    - **table_schema**: Schema da tabela
    - **natural_query**: Query em linguagem natural
    """
    logger.info("API: Gerar SQL", query=request.natural_query)

    try:
        model_manager = get_model_manager()
        agent = SQLAnalysisAgent(model_manager)

        sql = await agent.generate_sql(
            request.table_schema,
            request.natural_query
        )

        return AnalysisResponse(
            success=True,
            data={"sql": sql}
        )

    except Exception as e:
        logger.error("Erro ao gerar SQL", error=str(e))
        return AnalysisResponse(
            success=False,
            data=None,
            error=str(e)
        )


@router.post("/sql/explain", response_model=AnalysisResponse)
async def explain_sql(request: SQLExplainRequest):
    """
    Explica uma query SQL

    - **query**: Query SQL para explicar
    """
    logger.info("API: Explicar SQL")

    try:
        model_manager = get_model_manager()
        agent = SQLAnalysisAgent(model_manager)

        explanation = await agent.explain_query(request.query)

        return AnalysisResponse(
            success=True,
            data={"explanation": explanation}
        )

    except Exception as e:
        logger.error("Erro ao explicar SQL", error=str(e))
        return AnalysisResponse(
            success=False,
            data=None,
            error=str(e)
        )


# ============================================================================
# Status
# ============================================================================

@router.get("/status")
async def subagents_status():
    """Status dos sub-agentes"""
    try:
        model_manager = get_model_manager()

        return {
            "pdf_scholar": "available",
            "sql_analysis": "available",
            "models_loaded": list(model_manager.loaded_models.keys()),
            "current_large_model": model_manager.current_large_model
        }

    except Exception as e:
        logger.error("Erro ao obter status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
