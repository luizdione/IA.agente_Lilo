"""
extractor/section_splitter.py — Chunking IMRAD-aware.
Divide o paper em seções semânticas; sem seções, divide por tamanho com overlap.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

SECTION_HEADERS = re.compile(
    r"^\s*(abstract|introduction|introdução|methods?|material[s\s]*and[s\s]*methods?|"
    r"results?|resultados?|discussion|discussão|conclusion|conclus[aã]o|"
    r"references?|referências|acknowledgment|background)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# Seções de baixo valor para retrieval (bibliografia/agradecimentos): não indexar,
# senão o LLM ecoa números de citação das listas de referências.
SKIP_SECTIONS = {"references", "referências", "referencias", "acknowledgment",
                 "acknowledgments", "acknowledgement", "acknowledgements"}


@dataclass
class Chunk:
    paper_md5: str
    section: str
    text: str
    chunk_index: int


def split_into_chunks(paper_md5: str, full_text: str,
                      max_chars: int = 1200, overlap: int = 150,
                      skip_sections: set[str] = SKIP_SECTIONS) -> list[Chunk]:
    """1) tenta dividir por seções IMRAD; 2) senão, chunking por tamanho com overlap.
    Seções em skip_sections (references/acknowledgment) são ignoradas."""
    sections = _split_by_sections(full_text)
    if len(sections) < 3:
        sections = {"text": full_text}

    chunks: list[Chunk] = []
    idx = 0
    step = max(1, max_chars - overlap)
    for name, text in sections.items():
        if name.lower() in skip_sections:
            continue
        for i in range(0, len(text), step):
            piece = text[i:i + max_chars].strip()
            if len(piece) < 100:
                continue
            chunks.append(Chunk(paper_md5, name, piece, idx))
            idx += 1
    return chunks


def _split_by_sections(text: str) -> dict[str, str]:
    # re.split com 1 grupo capturante: [pre, header1, content1, header2, content2, ...]
    parts = SECTION_HEADERS.split(text)
    headers = SECTION_HEADERS.findall(text)
    sections: dict[str, str] = {}
    for i, header in enumerate(headers):
        content_idx = 2 * i + 2
        content = parts[content_idx] if content_idx < len(parts) else ""
        key = header.strip().lower()
        # cabeçalho repetido (ex.: 'Methods' duas vezes): ACUMULA em vez de sobrescrever,
        # senão o conteúdo da 1ª ocorrência era perdido (não indexado).
        sections[key] = (sections.get(key, "") + "\n" + content.strip()).strip()
    return sections
