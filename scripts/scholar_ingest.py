"""
scripts/ingest.py -- Pipeline de ingesta (resumivel e a prova de travamento).
Uso: python scripts/ingest.py /caminho/papers [/outro ...] [--limit N]

  1. Scan + deduplicacao
  2. RETOMA: pula papers cujo md5 ja esta no cerebro
  3. Por paper: extracao + metadados (CrossRef) em thread com TIMEOUT
     (um PDF problematico e PULADO, nao derruba a corrida)
  4. Chunking IMRAD + embeddings locais (CPU) + insercao no ChromaDB

Nao usa GPU: extracao (PyMuPDF) e embeddings (sentence-transformers) rodam em CPU;
metadados sao rede. Seguro para rodar junto com cargas de GPU (ex.: MD).
"""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scholaragent.scanner.crawler import scan_directories
from scholaragent.scanner.deduplicator import deduplicate
from scholaragent.extractor.pdf_parser import extract_pdf
from scholaragent.extractor.metadata_resolver import resolve_metadata
from scholaragent.extractor.section_splitter import split_into_chunks
from scholaragent.brain.embedder import Embedder
from scholaragent.brain.vector_store import BrainStore
from scholaragent.brain.classifier import ThemeClassifier

CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "")
PER_PAPER_TIMEOUT = int(os.environ.get("SCHOLAR_PAPER_TIMEOUT", "120"))  # segundos


def _existing_md5s(store) -> set[str]:
    """md5s de papers ja indexados (paginado p/ evitar 'too many SQL variables')."""
    out: set[str] = set()
    try:
        total = store.collection.count()
        step = 2000
        for off in range(0, total, step):
            got = store.collection.get(include=["metadatas"], limit=step, offset=off)
            for m in (got.get("metadatas") or []):
                if m.get("paper_md5"):
                    out.add(m["paper_md5"])
    except Exception as e:
        print(f"  [aviso] nao consegui ler md5s existentes ({e}); sem retomada", flush=True)
    return out


def main(roots: list[str], limit: int | None = None):
    print(f"Varrendo {len(roots)} diretorio(s)...", flush=True)
    all_files = scan_directories(roots)
    unique = deduplicate(all_files)
    print(f"  {len(all_files)} PDFs -> {len(unique)} unicos "
          f"({len(all_files) - len(unique)} duplicatas removidas)", flush=True)

    embedder = Embedder()
    store = BrainStore()
    classifier = ThemeClassifier(embedder)

    done = _existing_md5s(store)
    todo = [pf for pf in unique if pf.md5 not in done]
    print(f"  ja indexados: {len(done)} papers ({store.count()} chunks); "
          f"a processar: {len(todo)}", flush=True)
    if limit:
        todo = todo[:limit]
        print(f"  --limit: processando apenas {len(todo)} paper(s)", flush=True)

    def _io_work(pf):
        """So a parte propensa a travar (parse + rede). Sem acesso ao modelo."""
        extracted = extract_pdf(pf)
        resolved = asyncio.run(resolve_metadata(extracted, CROSSREF_EMAIL))
        chunks = split_into_chunks(pf.md5, resolved.full_text)
        return resolved, chunks

    new_papers = 0
    for i, pf in enumerate(todo, 1):
        # extracao+rede num worker com timeout: PDF travado e pulado
        ex = ThreadPoolExecutor(max_workers=1)
        try:
            resolved, chunks = ex.submit(_io_work, pf).result(timeout=PER_PAPER_TIMEOUT)
        except FuturesTimeout:
            print(f"  [timeout {PER_PAPER_TIMEOUT}s] pulando {pf.path.name}", flush=True)
            ex.shutdown(wait=False)
            continue
        except Exception as e:
            print(f"  [erro] {pf.path.name}: {e}", flush=True)
            ex.shutdown(wait=False)
            continue
        ex.shutdown(wait=False)

        if not chunks:
            continue
        # acesso ao modelo (classify/embed) so na thread principal -> sem corrida
        try:
            themes = classifier.classify(resolved.abstract)
            embeddings = embedder.embed_chunks(chunks)
            store.add_chunks(chunks, embeddings, {
                "title": resolved.title, "authors": resolved.authors,
                "year": resolved.year, "journal": resolved.journal,
                "doi": resolved.doi, "themes": themes, "path": str(pf.path),
            })
            new_papers += 1
        except Exception as e:
            print(f"  [erro-embed] {pf.path.name}: {e}", flush=True)
            continue

        if new_papers % 25 == 0:
            print(f"  ... {new_papers} novos (total chunks: {store.count()})", flush=True)

    print(f"Concluido. Papers novos nesta rodada: {new_papers} | "
          f"total de chunks: {store.count()}", flush=True)


if __name__ == "__main__":
    _args = sys.argv[1:]
    _limit = None
    if "--limit" in _args:
        _i = _args.index("--limit")
        _limit = int(_args[_i + 1])
        del _args[_i:_i + 2]
    main(_args or ["."], limit=_limit)
