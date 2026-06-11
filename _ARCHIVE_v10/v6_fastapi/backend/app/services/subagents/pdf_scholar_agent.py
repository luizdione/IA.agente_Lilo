"""
PDF Scholar Agent - Análise de documentos científicos
Integração do ScholarAgent com o sistema LILO
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

from app.services.model_manager import ModelManager, ModelRole

logger = structlog.get_logger()


class PDFScholarAgent:
    """Agente especializado em análise de PDFs científicos"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    async def analyze_pdf(
        self,
        pdf_path: str,
        mode: str = "simple"
    ) -> Dict[str, Any]:
        """
        Analisa PDF científico

        Args:
            pdf_path: Caminho do PDF
            mode: Modo de análise (simple, introduction, methods, graph)

        Returns:
            Análise estruturada
        """
        logger.info("Analisando PDF", path=pdf_path, mode=mode)

        # Extrair texto do PDF
        text = await self._extract_text(pdf_path)

        if not text:
            return {"error": "Não foi possível extrair texto do PDF"}

        # Análise conforme modo
        system_prompts = {
            "simple": """Você é um pesquisador sênior com expertise em bioquímica,
biologia molecular, parasitologia e biotecnologia. Resuma o artigo científico
fornecido de forma clara e concisa, destacando: objetivo, metodologia principal,
resultados-chave e conclusão.""",

            "introduction": """Você é um pesquisador sênior escrevendo a seção de
Introdução de um artigo científico. Com base no texto fornecido, produza um resumo
analítico que possa ser usado como suporte para redigir uma introdução. Inclua:
- Contexto do problema e lacuna no conhecimento
- Hipótese ou objetivo central dos autores
- Relevância para o campo
- Principais conceitos/moléculas/organismos mencionados""",

            "methods": """Você é um pesquisador sênior analisando a seção de Métodos.
Extraia e organize as informações metodológicas:
- Desenho experimental
- Modelos biológicos (organismos, linhagens celulares, enzimas-alvo)
- Técnicas analíticas e instrumentação
- Softwares e parâmetros computacionais
- Controles e critérios estatísticos""",
        }

        system_prompt = system_prompts.get(mode, system_prompts["simple"])

        # Truncar texto se muito longo (max 12k tokens ≈ 48k chars)
        if len(text) > 48000:
            text = text[:48000] + "\n\n[...truncado...]"

        prompt = f"""Texto do artigo científico:

{text}

Análise:"""

        analysis = await self.model_manager.generate(
            prompt=prompt,
            role=ModelRole.SCHOLAR,
            system_prompt=system_prompt,
            temperature=0.3
        )

        # Detectar DOI e metadata
        metadata = await self._extract_metadata(text)

        return {
            "mode": mode,
            "analysis": analysis,
            "metadata": metadata,
            "word_count": len(text.split()),
            "char_count": len(text)
        }

    async def _extract_text(self, pdf_path: str) -> Optional[str]:
        """Extrai texto de PDF"""
        try:
            # Usar PyPDF2 ou pdfplumber
            import PyPDF2

            path = Path(pdf_path)
            if not path.exists():
                logger.error("PDF não encontrado", path=pdf_path)
                return None

            text_parts = []

            with open(path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)

                for page_num, page in enumerate(reader.pages):
                    try:
                        text_parts.append(page.extract_text())
                    except Exception as e:
                        logger.warning("Erro ao extrair página",
                                     page=page_num, error=str(e))

            text = "\n\n".join(text_parts)

            logger.info("Texto extraído", pages=len(reader.pages), chars=len(text))
            return text

        except Exception as e:
            logger.error("Erro ao extrair texto do PDF", error=str(e))
            return None

    async def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extrai metadados do texto (DOI, título, autores)"""
        import re

        metadata = {}

        # Detectar DOI
        doi_pattern = r'10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+'
        doi_match = re.search(doi_pattern, text[:2000])  # Buscar no início
        if doi_match:
            metadata["doi"] = doi_match.group(0)

        # Detectar se é artigo científico (keywords)
        scientific_keywords = [
            "abstract", "introduction", "methods", "results",
            "discussion", "conclusion", "references"
        ]

        text_lower = text.lower()
        found_keywords = [kw for kw in scientific_keywords if kw in text_lower]

        metadata["is_scientific"] = len(found_keywords) >= 4
        metadata["found_sections"] = found_keywords

        return metadata

    async def batch_analyze(
        self,
        pdf_dir: str,
        mode: str = "simple"
    ) -> List[Dict[str, Any]]:
        """
        Analisa múltiplos PDFs em lote

        Args:
            pdf_dir: Diretório com PDFs
            mode: Modo de análise

        Returns:
            Lista de análises
        """
        from pathlib import Path

        pdf_path = Path(pdf_dir)

        if not pdf_path.exists():
            return [{"error": f"Diretório não encontrado: {pdf_dir}"}]

        results = []

        for pdf_file in pdf_path.glob("*.pdf"):
            try:
                result = await self.analyze_pdf(str(pdf_file), mode)
                result["file"] = pdf_file.name
                results.append(result)
            except Exception as e:
                logger.error("Erro ao processar PDF", file=pdf_file.name, error=str(e))
                results.append({
                    "file": pdf_file.name,
                    "error": str(e)
                })

        logger.info("Análise em lote concluída", total=len(results))
        return results
