"""
scripts/scholar_refresh_metadata.py — Re-resolve metadados (título/autores/ano/DOI) dos
papers JÁ indexados e atualiza o ChromaDB IN-PLACE (sem re-embeddar). Resumível: pula
papers que já têm título decente + autores. CPU/rede (CrossRef), GPU-free.

Uso (da raiz do Lilo):
  python scripts/scholar_refresh_metadata.py "D:\\OneDrive\\Documentos\\Workaholics\\Artigos PDF"
  python scripts/scholar_refresh_metadata.py <pasta> --force   # refaz todos
"""
from __future__ import annotations
import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scholaragent.scanner.crawler import scan_directories
from scholaragent.extractor.pdf_parser import extract_pdf
from scholaragent.extractor.metadata_resolver import resolve_metadata, _good_title
from scholaragent.brain.vector_store import BrainStore

CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "")


def _chunks_by_md5(store):
    out = defaultdict(list)
    n = store.collection.count()
    for off in range(0, n, 2000):
        g = store.collection.get(include=["metadatas"], limit=2000, offset=off)
        for cid, m in zip(g["ids"], g["metadatas"]):
            md5 = m.get("paper_md5")
            if md5:
                out[md5].append((cid, m))
    return out


async def main(roots: list[str], force: bool = False):
    store = BrainStore()
    by_md5 = _chunks_by_md5(store)
    print(f"papers no cerebro: {len(by_md5)} | chunks: {store.collection.count()}", flush=True)

    print("escaneando PDFs no disco para mapear md5 -> caminho...", flush=True)
    path_by_md5 = {pf.md5: pf for pf in scan_directories(roots)}
    print(f"PDFs no disco: {len(path_by_md5)}", flush=True)

    updated = skipped_ok = no_pdf = no_gain = 0
    for md5, chunks in by_md5.items():
        meta0 = chunks[0][1]
        if not force and _good_title(meta0.get("title")) and (meta0.get("authors") or "").strip():
            skipped_ok += 1
            continue
        pf = path_by_md5.get(md5)
        if pf is None:
            no_pdf += 1
            continue
        try:
            resolved = await resolve_metadata(extract_pdf(pf), CROSSREF_EMAIL)
        except Exception as e:
            print(f"  [erro] {md5[:8]}: {e}", flush=True)
            continue
        if not _good_title(resolved.title) and not resolved.authors:
            no_gain += 1
            continue
        ids = [cid for cid, _ in chunks]
        new_metas = []
        for _cid, m in chunks:
            mm = dict(m)
            if _good_title(resolved.title):
                mm["title"] = resolved.title
            if resolved.authors:
                mm["authors"] = "; ".join(resolved.authors)
            if resolved.year:
                mm["year"] = str(resolved.year)
            if resolved.journal:
                mm["journal"] = resolved.journal
            if resolved.doi:
                mm["doi"] = resolved.doi
            new_metas.append(mm)
        store.collection.update(ids=ids, metadatas=new_metas)
        updated += 1
        if updated % 25 == 0:
            print(f"  ... {updated} papers atualizados", flush=True)

    print(f"Concluido. Atualizados: {updated} | ja-ok (pulados): {skipped_ok} | "
          f"sem PDF: {no_pdf} | sem ganho: {no_gain}", flush=True)


if __name__ == "__main__":
    _args = [a for a in sys.argv[1:] if a != "--force"]
    _force = "--force" in sys.argv
    main_roots = _args or [r"D:\OneDrive\Documentos\Workaholics\Artigos PDF"]
    asyncio.run(main(main_roots, force=_force))
