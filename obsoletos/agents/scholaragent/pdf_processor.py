"""
pdf_processor.py
Extração de texto, metadados e imagens de PDFs científicos via PyMuPDF.
"""

import fitz  # PyMuPDF
import base64
import io
import re
from pathlib import Path
from typing import Optional


def extract_full_text(pdf_path: str) -> str:
    """Extrai texto completo do PDF, página por página."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"--- Página {i+1} ---\n{text}")
    doc.close()
    return "\n\n".join(pages)


def extract_sections(pdf_path: str) -> dict:
    """
    Tenta identificar seções típicas de artigo científico no texto extraído.
    Heurística baseada em headings comuns (Abstract, Introduction, Methods, etc.).
    """
    full_text = extract_full_text(pdf_path)

    # Padrões comuns de seções (EN/PT)
    section_patterns = {
        "abstract": r"(?i)\b(abstract|resumo)\b",
        "introduction": r"(?i)\b(introduction|introdução|introdu[cç][aã]o)\b",
        "methods": r"(?i)\b(methods?|materials?\s*(?:and|e)\s*methods?|metodologia|m[eé]todos?)\b",
        "results": r"(?i)\b(results?|resultados?)\b",
        "discussion": r"(?i)\b(discussion|discuss[aã]o)\b",
        "conclusion": r"(?i)\b(conclusions?|conclus[oõ]es?)\b",
        "references": r"(?i)\b(references|refer[eê]ncias|bibliography|bibliografia)\b",
    }

    lines = full_text.split("\n")
    section_starts = {}

    for idx, line in enumerate(lines):
        clean = line.strip()
        if len(clean) > 100:
            continue  # Provavelmente não é heading
        for section, pattern in section_patterns.items():
            if section not in section_starts and re.search(pattern, clean):
                section_starts[section] = idx

    # Extrair texto entre seções
    sorted_sections = sorted(section_starts.items(), key=lambda x: x[1])
    sections = {}
    for i, (name, start) in enumerate(sorted_sections):
        end = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(lines)
        sections[name] = "\n".join(lines[start:end]).strip()

    sections["full_text"] = full_text
    return sections


def extract_images(pdf_path: str, min_size: int = 5000) -> list[dict]:
    """
    Extrai imagens do PDF (potenciais figuras/gráficos).
    Filtra por tamanho mínimo em bytes para descartar ícones/logos.
    Retorna lista de dicts com {page, index, base64, width, height, ext}.
    """
    doc = fitz.open(pdf_path)
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        img_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and len(base_image["image"]) >= min_size:
                    img_b64 = base64.b64encode(base_image["image"]).decode("utf-8")
                    images.append({
                        "page": page_num + 1,
                        "index": img_idx,
                        "base64": img_b64,
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                        "ext": base_image.get("ext", "png"),
                    })
            except Exception:
                continue

    doc.close()
    return images


def extract_metadata(pdf_path: str) -> dict:
    """Extrai metadados do PDF (título, autor, etc.)."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}
    meta["page_count"] = doc.page_count
    doc.close()
    return meta


def extract_references_section(pdf_path: str) -> Optional[str]:
    """Tenta extrair apenas a seção de referências do PDF."""
    sections = extract_sections(pdf_path)
    return sections.get("references")
