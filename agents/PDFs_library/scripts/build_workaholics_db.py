"""
PDFs_library/scripts/build_workaholics_db.py  (v2 — focado em Artigos PDF)
==========================================================================
Indexador offline de artigos cientificos. Varre por padrao
    D:\\OneDrive\\Documentos\\Workaholics\\Artigos PDF
e cria UMA TABELA SQLite por subdiretorio (= tema).

ZERO TOKENS — apenas heuristicas locais (PyMuPDF + regex).

Schema (workaholics.db):
  _index(table_name, dir_path, n_pdfs, last_scan)
  _favorites(table_name, starred, sort_order, updated_at)
  _curation(file_path, contribution_to_project, dataset_status, updated_at)
  _meta(key, value)
  <tabela_X>(id, file_path, file_name, file_size, file_mtime, file_hash,
             title, authors, year, journal, doi, issn, abstract, n_pages,
             indexed_journal, paper_type, species, head_text, error,
             scanned_at)

Uso:
    python build_workaholics_db.py
    python build_workaholics_db.py --root "D:\\OneDrive\\Documentos\\Workaholics\\Artigos PDF"
    python build_workaholics_db.py --no-resume

Pre-req:
    pip install pymupdf
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import fitz  # type: ignore
except ImportError:
    print("ERRO: PyMuPDF nao instalado. Rode: pip install pymupdf",
          file=sys.stderr)
    sys.exit(1)

# Silencia warnings nativos do MuPDF (perfis ICC, fontes, jbig2dec)
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
except (AttributeError, Exception):
    pass

# -- Config -----------------------------------------------------------------

DEFAULT_ROOT = r"D:\OneDrive\Documentos\Workaholics\Artigos PDF"
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "workaholics.db"

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
ISSN_RE = re.compile(r"\bISSN[:\s]*([0-9]{4}-[0-9]{3}[0-9X])\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Regex de tipo de paper (heuristica)
RE_REVIEW = re.compile(
    r"\b(systematic review|meta[-\s]?analysis|narrative review|review article|"
    r"revis[aã]o sistem[aá]tica|revis[aã]o)\b", re.IGNORECASE)
RE_ORIGINAL = re.compile(
    r"\b(original article|research article|original research)\b", re.IGNORECASE)
RE_LETTER = re.compile(r"\b(letter to the editor|short communication)\b",
                        re.IGNORECASE)

# Especies (BR + EN + binomial)
SPECIES_PATTERNS = [
    (r"\bBos\s+taurus\b",        "Bos taurus"),
    (r"\bBos\s+indicus\b",       "Bos indicus"),
    (r"\bBos\s+primigenius\b",   "Bos primigenius"),
    (r"\bSus\s+scrofa\b",        "Sus scrofa (suinos)"),
    (r"\bGallus\s+gallus\b",     "Gallus gallus (aves)"),
    (r"\bOvis\s+aries\b",        "Ovis aries (ovinos)"),
    (r"\bCapra\s+hircus\b",      "Capra hircus (caprinos)"),
    (r"\bMus\s+musculus\b",      "Mus musculus (camundongo)"),
    (r"\bRattus\s+norvegicus\b", "Rattus norvegicus (rato)"),
    (r"\bbovine\b",              "bovinos"),
    (r"\bovine\b",               "ovinos"),
    (r"\bcaprine\b",             "caprinos"),
    (r"\bporcine\b",             "suinos"),
    (r"\bavian\b",               "aves"),
    (r"\bcattle\b",              "bovinos"),
    (r"\bsheep\b",               "ovinos"),
    (r"\bgoat[s]?\b",            "caprinos"),
    (r"\bswine\b|\bpig[s]?\b",   "suinos"),
    (r"\bpoultry\b|\bchicken[s]?\b", "aves"),
    (r"\bzebrafish\b",           "Danio rerio (peixe-zebra)"),
    (r"\bArabidopsis\b",         "Arabidopsis"),
    (r"\bDrosophila\b",          "Drosophila"),
]

# Limites
MAX_PDF_BYTES = 200 * 1024 * 1024
HEAD_PAGES = 4
HEAD_TEXT_CHARS = 8000


# -- Utilidades --------------------------------------------------------------

def sanitize_table_name(name: str) -> str:
    """Nome de diretorio -> identifier SQL valido."""
    n = name.strip()
    repl = {"ã":"a","á":"a","â":"a","à":"a","é":"e","ê":"e","è":"e",
            "í":"i","ì":"i","ó":"o","ô":"o","õ":"o","ò":"o",
            "ú":"u","ü":"u","ù":"u","ç":"c","ñ":"n",
            "Ã":"A","Á":"A","Â":"A","À":"A","É":"E","Ê":"E",
            "Í":"I","Ó":"O","Ô":"O","Õ":"O","Ú":"U","Ç":"C"}
    for k, v in repl.items():
        n = n.replace(k, v)
    n = re.sub(r"[^A-Za-z0-9_]", "_", n)
    n = re.sub(r"_+", "_", n).strip("_")
    if not n:
        n = "root"
    if n[0].isdigit():
        n = "t_" + n
    return n[:60]


class _SilenceStderr:
    """Silencia warnings nativos do MuPDF redirecionando FD 2 -> devnull."""
    def __enter__(self):
        try:
            self._null = open(os.devnull, "w")
            self._saved = os.dup(2)
            os.dup2(self._null.fileno(), 2)
        except (OSError, AttributeError):
            self._null = None
            self._saved = None
        return self

    def __exit__(self, *exc):
        try:
            if self._saved is not None:
                os.dup2(self._saved, 2)
                os.close(self._saved)
            if self._null is not None:
                self._null.close()
        except OSError:
            pass


# -- Heuristicas adicionais --------------------------------------------------

def detect_paper_type(text: str) -> str:
    """Classifica o tipo do paper a partir do head_text."""
    if RE_REVIEW.search(text):
        return "Revisao sistematica" if "systematic" in text.lower() else "Revisao"
    if RE_ORIGINAL.search(text):
        return "Artigo original"
    if RE_LETTER.search(text):
        return "Carta/comunicacao"
    return ""


def detect_species(text: str) -> str:
    """Extrai lista de especies mencionadas no head_text."""
    found: list[str] = []
    for pat, label in SPECIES_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            if label not in found:
                found.append(label)
        if len(found) >= 6:
            break
    return ", ".join(found)


# -- Extracao de metadados ---------------------------------------------------

def extract_pdf_meta(pdf_path: Path) -> dict:
    info = {
        "title": "", "authors": "", "year": "", "journal": "",
        "doi": "", "issn": "", "abstract": "", "n_pages": 0,
        "indexed_journal": 0, "paper_type": "", "species": "",
        "head_text": "", "error": "",
    }
    with _SilenceStderr():
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            info["error"] = f"open_failed: {e}"
            return info

        try:
            info["n_pages"] = len(doc)
            meta = doc.metadata or {}
            info["title"] = (meta.get("title") or "").strip()
            info["authors"] = (meta.get("author") or "").strip()

            head_pages_text = []
            for i in range(min(HEAD_PAGES, info["n_pages"])):
                try:
                    head_pages_text.append(doc[i].get_text("text"))
                except Exception:
                    pass
            head_text = "\n".join(head_pages_text)[:HEAD_TEXT_CHARS]
            info["head_text"] = head_text

            m_doi = DOI_RE.search(head_text)
            if m_doi:
                info["doi"] = m_doi.group(0).rstrip(".,;)")

            m_issn = ISSN_RE.search(head_text)
            if m_issn:
                info["issn"] = m_issn.group(1).upper()

            years = [int(m.group(0)) for m in YEAR_RE.finditer(head_text)]
            years = [y for y in years if 1900 <= y <= datetime.now().year + 1]
            if years:
                info["year"] = str(years[0])

            if info["doi"] or info["issn"]:
                info["indexed_journal"] = 1

            # Titulo via primeira linha longa
            if not info["title"] and head_pages_text:
                first_page_lines = [
                    ln.strip() for ln in head_pages_text[0].splitlines()
                    if 25 <= len(ln.strip()) <= 220
                ]
                if first_page_lines:
                    info["title"] = first_page_lines[0]

            # Abstract
            abs_match = re.search(
                r"\bAbstract\b[:\s\-]*(.{50,2500}?)"
                r"(?=\b(Introduction|Keywords|Background|1\.|I\.|Resumo)\b)",
                head_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if abs_match:
                info["abstract"] = re.sub(
                    r"\s+", " ", abs_match.group(1)).strip()[:2000]

            # Journal
            jm = re.search(
                r"((?:Journal of|International Journal of|Frontiers in|"
                r"Nature|Science|PNAS|PLoS|Cell|Biochim|Mol|"
                r"Annual Review|Trends in|BMC|FEBS|Genome|Genes|"
                r"Animal|Veterinary|Livestock)[A-Za-z &]{2,90})",
                head_text,
            )
            if jm:
                info["journal"] = jm.group(1).strip()[:140]

            # Heuristicas extras
            info["paper_type"] = detect_paper_type(head_text)
            info["species"] = detect_species(head_text)

        except Exception as e:
            info["error"] = f"extract_failed: {e}"
        finally:
            try:
                doc.close()
            except Exception:
                pass

    return info


# -- Banco -------------------------------------------------------------------

def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _index (
            table_name TEXT PRIMARY KEY,
            dir_path   TEXT NOT NULL,
            n_pdfs     INTEGER DEFAULT 0,
            last_scan  TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _favorites (
            table_name TEXT PRIMARY KEY,
            starred    INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            updated_at TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _curation (
            file_path TEXT PRIMARY KEY,
            contribution_to_project TEXT DEFAULT '',
            dataset_status          TEXT DEFAULT '',
            updated_at              TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _meta (
            key TEXT PRIMARY KEY, value TEXT
        )""")
    conn.commit()


def _ensure_pdf_table(conn: sqlite3.Connection, table_name: str):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path       TEXT UNIQUE NOT NULL,
            file_name       TEXT NOT NULL,
            file_size       INTEGER,
            file_mtime      TEXT,
            file_hash       TEXT,
            title           TEXT,
            authors         TEXT,
            year            TEXT,
            journal         TEXT,
            doi             TEXT,
            issn            TEXT,
            abstract        TEXT,
            n_pages         INTEGER,
            indexed_journal INTEGER DEFAULT 0,
            paper_type      TEXT,
            species         TEXT,
            head_text       TEXT,
            error           TEXT,
            scanned_at      TEXT NOT NULL
        )""")
    conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_year '
                 f'ON "{table_name}"(year)')
    conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_doi '
                 f'ON "{table_name}"(doi)')
    conn.commit()


def _file_already_indexed(conn: sqlite3.Connection, table: str,
                           file_path: str, file_size: int,
                           file_mtime: str) -> bool:
    cur = conn.execute(
        f'SELECT file_size, file_mtime FROM "{table}" WHERE file_path = ?',
        (file_path,),
    )
    row = cur.fetchone()
    if not row:
        return False
    return row[0] == file_size and row[1] == file_mtime


# -- Scanner -----------------------------------------------------------------

def scan_directory(root: Path, db_path: Path,
                    resume: bool = True,
                    limit: Optional[int] = None,
                    verbose: bool = True) -> dict:
    if not root.exists():
        raise FileNotFoundError(f"Diretorio nao encontrado: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Nao e diretorio: {root}")

    t0 = time.time()
    stats = {"dirs": 0, "pdfs_total": 0, "pdfs_new": 0,
             "pdfs_skipped": 0, "errors": 0, "time_s": 0.0}

    conn = _connect(db_path)
    try:
        _init_schema(conn)
        conn.execute("INSERT OR REPLACE INTO _meta VALUES (?, ?)",
                     ("root", str(root)))
        conn.execute("INSERT OR REPLACE INTO _meta VALUES (?, ?)",
                     ("last_scan", datetime.now().isoformat()))
        conn.commit()

        # Coleta diretorios com PDFs
        dirs_with_pdfs: dict[Path, list[Path]] = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in
                           {"__pycache__", ".git", ".venv", "venv",
                            "node_modules", ".idea", ".vscode"}]
            pdfs = [Path(dirpath) / f for f in filenames
                    if f.lower().endswith(".pdf")]
            if pdfs:
                dirs_with_pdfs[Path(dirpath)] = pdfs

        if verbose:
            print(f"[Scanner] {len(dirs_with_pdfs)} diretorios com PDFs "
                  f"({sum(len(v) for v in dirs_with_pdfs.values())} arquivos)")

        processed = 0
        for d, pdfs in dirs_with_pdfs.items():
            stats["dirs"] += 1
            rel = d.relative_to(root) if d != root else Path(".")
            base_name = "_".join(p for p in rel.parts) or root.name
            table_name = sanitize_table_name(base_name)
            _ensure_pdf_table(conn, table_name)

            if verbose:
                print(f"\n[{stats['dirs']}/{len(dirs_with_pdfs)}] "
                      f"{rel} -> `{table_name}` ({len(pdfs)} PDFs)")

            for pdf in pdfs:
                stats["pdfs_total"] += 1
                if limit is not None and processed >= limit:
                    if verbose:
                        print(f"[Scanner] Limite atingido. Parando.")
                    break

                try:
                    st = pdf.stat()
                except OSError as e:
                    stats["errors"] += 1
                    continue

                if st.st_size > MAX_PDF_BYTES:
                    stats["pdfs_skipped"] += 1
                    continue

                file_path = str(pdf)
                file_mtime = datetime.fromtimestamp(st.st_mtime).isoformat()

                if resume and _file_already_indexed(
                        conn, table_name, file_path, st.st_size, file_mtime):
                    stats["pdfs_skipped"] += 1
                    processed += 1
                    continue

                try:
                    with open(pdf, "rb") as f:
                        head = f.read(65536)
                    file_hash = hashlib.sha1(head).hexdigest()[:16]
                except OSError:
                    file_hash = ""

                meta = extract_pdf_meta(pdf)
                if meta.get("error"):
                    stats["errors"] += 1

                conn.execute(
                    f'INSERT OR REPLACE INTO "{table_name}" '
                    f'(file_path, file_name, file_size, file_mtime, file_hash,'
                    f' title, authors, year, journal, doi, issn, abstract,'
                    f' n_pages, indexed_journal, paper_type, species,'
                    f' head_text, error, scanned_at) '
                    f'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (
                        file_path, pdf.name, st.st_size, file_mtime, file_hash,
                        meta["title"], meta["authors"], meta["year"],
                        meta["journal"], meta["doi"], meta["issn"],
                        meta["abstract"], meta["n_pages"],
                        meta["indexed_journal"], meta["paper_type"],
                        meta["species"], meta["head_text"],
                        meta["error"], datetime.now().isoformat(),
                    ),
                )
                stats["pdfs_new"] += 1
                processed += 1

                if verbose and stats["pdfs_new"] % 25 == 0:
                    conn.commit()
                    print(f"    ... {stats['pdfs_new']} novos indexados")

            conn.commit()
            cur = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            total_in_table = cur.fetchone()[0]
            conn.execute(
                "INSERT OR REPLACE INTO _index "
                "(table_name, dir_path, n_pdfs, last_scan) VALUES (?,?,?,?)",
                (table_name, str(d), total_in_table,
                 datetime.now().isoformat()),
            )
            conn.commit()

            if limit is not None and processed >= limit:
                break

    finally:
        conn.close()

    stats["time_s"] = round(time.time() - t0, 2)
    return stats


# -- CLI ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help=f"Raiz a varrer (default: {DEFAULT_ROOT})")
    ap.add_argument("--out", default=str(DEFAULT_DB),
                    help=f"DB de saida (default: {DEFAULT_DB})")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    db_path = Path(args.out)

    print(f"[Scanner] root = {root}")
    print(f"[Scanner] db   = {db_path}")
    print(f"[Scanner] resume = {not args.no_resume}")
    print()

    try:
        stats = scan_directory(
            root=root, db_path=db_path,
            resume=not args.no_resume, limit=args.limit,
            verbose=not args.quiet,
        )
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(2)

    print("\n[Scanner] === Concluido ===")
    print(f"  Diretorios processados : {stats['dirs']}")
    print(f"  PDFs encontrados       : {stats['pdfs_total']}")
    print(f"  PDFs novos indexados   : {stats['pdfs_new']}")
    print(f"  PDFs ignorados (cache) : {stats['pdfs_skipped']}")
    print(f"  Erros                  : {stats['errors']}")
    print(f"  Tempo                  : {stats['time_s']}s")
    print(f"  Banco                  : {db_path}")


if __name__ == "__main__":
    main()
