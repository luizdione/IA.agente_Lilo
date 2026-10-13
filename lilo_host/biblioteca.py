"""Biblioteca de PDFs do dono (grupo conhecimento): indice proprio, incremental e sob demanda.

Fonte   LILO_BIBLIOTECA_PDFS  (padrao: C:\\Users\\luizd\\OneDrive\\Documentos\\Workaholics\\Artigos PDF)
Indice  LILO_BIBLIOTECA       (padrao: E:\\data\\lilo\\biblioteca, fora do OneDrive)
  chroma\\          vetores (cosseno) da colecao `trechos`
  biblioteca.db    SQLite: `docs` (hash, caminho, titulo, estado) + FTS5 `trechos` (BM25)
  status.json      progresso da indexacao (resumivel)

Embeddings densos do BAAI/bge-m3 (sentence-transformers, normalizados). Indexacao na GPU
(fp16) quando o interruptor estiver on e houver CUDA; consulta SEMPRE na CPU, sem disputar
VRAM com o `lilo`. Busca hibrida: top-k vetorial + top-k BM25 -> fusao RRF, um resultado
por documento. Incremental por SHA-1 do arquivo: so entra PDF novo ou alterado; nada de
reindexacao continua (D-0016).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path

from .comum import erro

PDFS = Path(os.environ.get("LILO_BIBLIOTECA_PDFS",
                           r"C:\Users\luizd\OneDrive\Documentos\Workaholics\Artigos PDF"))
INDICE = Path(os.environ.get("LILO_BIBLIOTECA", r"E:\data\lilo\biblioteca"))
# Pesos locais em safetensors (transformers >= 5.5 recusa pytorch_model.bin com torch < 2.6):
# pasta montada a partir do cache do HF (modelo + tokenizer). Sem ela, cai no nome do hub.
_MODELO_LOCAL = Path(r"E:\data\lilo\modelos\bge-m3")
MODELO = os.environ.get("LILO_BIBLIOTECA_MODELO",
                        str(_MODELO_LOCAL) if (_MODELO_LOCAL / "model.safetensors").exists() else "BAAI/bge-m3")
TRECHO = 1000          # caracteres por trecho
SOBREPOSICAO = 150
TRECHO_MIN = 80
LOTE = 32              # textos por lote no encode
K = 20                 # candidatos por via (vetorial e BM25) antes da fusao
RRF_K = 60


def _agora() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------------- armazem
def _db(indice: Path) -> sqlite3.Connection:
    indice.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(indice / "biblioteca.db"))
    con.execute("""CREATE TABLE IF NOT EXISTS docs(
        hash TEXT PRIMARY KEY, caminho TEXT UNIQUE, nome TEXT, titulo TEXT, paginas INTEGER,
        trechos INTEGER, bytes INTEGER, mtime REAL, indexado_em TEXT, erro TEXT)""")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS trechos USING fts5(
        hash UNINDEXED, idx UNINDEXED, pagina UNINDEXED, texto,
        tokenize='unicode61 remove_diacritics 2')""")
    return con


def _colecao(indice: Path):
    import chromadb
    from chromadb.config import Settings
    cli = chromadb.PersistentClient(path=str(indice / "chroma"),
                                    settings=Settings(anonymized_telemetry=False))
    return cli.get_or_create_collection("trechos", metadata={"hnsw:space": "cosine"})


def _gravar_status(indice: Path, st: dict) -> None:
    st["atualizado"] = _agora()
    (indice / "status.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------- extracao
def hash_arquivo(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def extrair(p: Path) -> tuple[str, list[str]]:
    """(titulo, texto de cada pagina). Titulo: metadado do PDF ou 1a linha util da pagina 1."""
    import fitz  # PyMuPDF
    with fitz.open(str(p)) as doc:
        paginas = [pg.get_text("text") for pg in doc]
        titulo = " ".join(((doc.metadata or {}).get("title") or "").split())
    if len(titulo) < 6 or titulo.lower().startswith(("untitled", "microsoft word", "doi:")):
        titulo = ""
        for linha in (paginas[0] if paginas else "").splitlines():
            linha = " ".join(linha.split())
            if len(linha) >= 12:
                titulo = linha[:150]
                break
    return titulo or p.stem, paginas


def fatiar(paginas: list[str], tamanho: int = TRECHO, sobre: int = SOBREPOSICAO) -> list[tuple[int, str]]:
    """[(pagina, trecho)]: janelas de ~`tamanho` caracteres, cortadas em fim de frase,
    com sobreposicao; pagina sem texto util (imagem) e pulada."""
    out: list[tuple[int, str]] = []
    for n, texto in enumerate(paginas, 1):
        texto = re.sub(r"[ \t]+", " ", texto or "").strip()
        if len(texto) < TRECHO_MIN:
            continue
        i = 0
        while i < len(texto):
            fim = min(len(texto), i + tamanho)
            if fim < len(texto):
                corte = texto.rfind(". ", i + tamanho // 2, fim)
                if corte > 0:
                    fim = corte + 1
            pedaco = texto[i:fim].strip()
            if len(pedaco) >= TRECHO_MIN:
                out.append((n, pedaco))
            if fim >= len(texto):
                break
            i = max(fim - sobre, i + 1)
    return out


# ------------------------------------------------------------------ embedder
class Embedder:
    """bge-m3 via sentence-transformers. `cuda` em fp16 para indexar; `cpu` para consultar."""

    def __init__(self, dispositivo: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self.dispositivo = dispositivo
        self.modelo = SentenceTransformer(MODELO, device=dispositivo)
        self.modelo.max_seq_length = 1024   # trechos tem ~300 tokens; limita RAM/VRAM
        if dispositivo.startswith("cuda"):
            self.modelo.half()

    def codificar(self, textos: list[str]):
        return self.modelo.encode(textos, batch_size=LOTE, normalize_embeddings=True,
                                  convert_to_numpy=True, show_progress_bar=False)


_consulta: Embedder | None = None


def embedder_consulta() -> Embedder:
    """Singleton na CPU para as buscas (carrega na 1a consulta, ~5 s)."""
    global _consulta
    if _consulta is None:
        _consulta = Embedder("cpu")
    return _consulta


# ------------------------------------------------------------------ indexar
def _indexar_doc(con, col, emb, p: Path, h: str, stt: os.stat_result) -> int:
    titulo, paginas = extrair(p)
    pedacos = fatiar(paginas)
    antigo = con.execute("SELECT hash FROM docs WHERE caminho=?", (str(p),)).fetchone()
    for hh in {h, antigo[0] if antigo else None} - {None}:     # versao anterior / rodada interrompida
        con.execute("DELETE FROM trechos WHERE hash=?", (hh,))
        con.execute("DELETE FROM docs WHERE hash=?", (hh,))
        try:
            col.delete(where={"hash": hh})
        except Exception:  # noqa: BLE001 — colecao vazia ou sem esse hash
            pass
    if pedacos:
        vetores = emb.codificar([t for _, t in pedacos])
        for i in range(0, len(pedacos), 500):
            fatia = pedacos[i:i + 500]
            col.add(ids=["%s:%d" % (h, i + j) for j in range(len(fatia))],
                    embeddings=vetores[i:i + len(fatia)].tolist(),
                    documents=[t for _, t in fatia],
                    metadatas=[{"hash": h, "idx": i + j, "pagina": pg, "nome": p.name}
                               for j, (pg, _) in enumerate(fatia)])
        con.executemany("INSERT INTO trechos(hash, idx, pagina, texto) VALUES(?,?,?,?)",
                        [(h, i, pg, t) for i, (pg, t) in enumerate(pedacos)])
    con.execute("INSERT OR REPLACE INTO docs(hash, caminho, nome, titulo, paginas, trechos, bytes, mtime,"
                " indexado_em, erro) VALUES(?,?,?,?,?,?,?,?,?,NULL)",
                (h, str(p), p.name, titulo, len(paginas), len(pedacos), stt.st_size, stt.st_mtime, _agora()))
    con.commit()
    return len(pedacos)


def indexar(pasta: Path | None = None, indice: Path | None = None, dispositivo: str = "cpu",
            limite: int = 0, embedder: Embedder | None = None, log=print) -> dict:
    """Indexa os PDFs novos/alterados de `pasta`. Idempotente e resumivel: PDF com o mesmo
    tamanho+mtime (ou o mesmo SHA-1) ja indexado e pulado. Falha num PDF nao para a rodada."""
    pasta = pasta or PDFS
    indice = indice or INDICE
    pdfs = sorted(p for p in pasta.rglob("*.pdf") if p.is_file())
    if limite:
        pdfs = pdfs[:limite]
    con = _db(indice)
    col = _colecao(indice)
    conhecidos = {r[0]: r for r in con.execute("SELECT caminho, hash, bytes, mtime, erro FROM docs")}
    st = {"total": len(pdfs), "feitos": 0, "novos": 0, "pulados": 0, "falhas": 0, "trechos_novos": 0,
          "atual": "", "dispositivo": dispositivo, "pasta": str(pasta), "inicio": _agora(), "fim": None}
    _gravar_status(indice, st)
    emb = embedder
    t0 = time.time()
    for p in pdfs:
        st["atual"] = p.name
        try:
            stt = p.stat()
            c = conhecidos.get(str(p))
            if c and c[2] == stt.st_size and abs((c[3] or 0) - stt.st_mtime) < 1 and not c[4]:
                st["pulados"] += 1                       # inalterado: nem re-hash
            else:
                h = hash_arquivo(p)
                if c and c[1] == h and not c[4]:         # mesmo conteudo, so metadados mudaram
                    con.execute("UPDATE docs SET bytes=?, mtime=? WHERE caminho=?", (stt.st_size, stt.st_mtime, str(p)))
                    con.commit()
                    st["pulados"] += 1
                else:
                    if emb is None:
                        emb = Embedder(dispositivo)
                    st["trechos_novos"] += _indexar_doc(con, col, emb, p, h, stt)
                    st["novos"] += 1
        except Exception as e:  # noqa: BLE001 — PDF cifrado/corrompido: registra e segue
            st["falhas"] += 1
            chave = "erro:" + hashlib.sha1(str(p).encode("utf-8")).hexdigest()
            con.execute("DELETE FROM docs WHERE caminho=?", (str(p),))
            con.execute("INSERT OR REPLACE INTO docs(hash, caminho, nome, erro, indexado_em) VALUES(?,?,?,?,?)",
                        (chave, str(p), p.name, "%s: %s" % (type(e).__name__, str(e)[:200]), _agora()))
            con.commit()
            log("FALHA %s: %s" % (p.name, e))
        st["feitos"] += 1
        if st["feitos"] % 10 == 0 or st["feitos"] == st["total"]:
            dec = time.time() - t0
            st["eta_min"] = round((st["total"] - st["feitos"]) * dec / max(st["feitos"], 1) / 60, 1)
            _gravar_status(indice, st)
            log("%d/%d  novos %d  pulados %d  falhas %d  (%.0f s)" % (
                st["feitos"], st["total"], st["novos"], st["pulados"], st["falhas"], dec))
    st["atual"] = ""
    st["fim"] = _agora()
    st["segundos"] = round(time.time() - t0, 1)
    _gravar_status(indice, st)
    con.close()
    return st


# -------------------------------------------------------------------- buscar
def buscar(consulta: str, n: int = 5, indice: Path | None = None,
           embedder: Embedder | None = None) -> list[dict] | str:
    """Top-n documentos por fusao RRF (vetorial + BM25); melhor trecho de cada um."""
    indice = indice or INDICE
    if not (indice / "biblioteca.db").exists():
        return erro("biblioteca ainda nao indexada: rode  .\\lilo.ps1 indexar")
    q = " ".join((consulta or "").split())
    if not q:
        return []
    con = _db(indice)
    pontos: dict[str, float] = {}                 # "hash:idx" -> pontuacao RRF
    dados: dict[str, tuple[str, int, str]] = {}   # "hash:idx" -> (hash, pagina, texto)

    col = _colecao(indice)
    total = col.count()
    if total:
        emb = embedder or embedder_consulta()
        v = emb.codificar([q])[0].tolist()
        r = col.query(query_embeddings=[v], n_results=min(K, total), include=["metadatas", "documents"])
        for posto, (i, m, d) in enumerate(zip(r["ids"][0], r["metadatas"][0], r["documents"][0]), 1):
            pontos[i] = pontos.get(i, 0.0) + 1.0 / (RRF_K + posto)
            dados[i] = (m["hash"], int(m["pagina"]), d)

    toks = [t for t in re.findall(r"\w+", q.lower()) if len(t) >= 3][:12]
    if toks:
        fts = " OR ".join('"%s"' % t for t in toks)
        linhas = con.execute("SELECT hash, idx, pagina, texto FROM trechos WHERE trechos MATCH ?"
                             " ORDER BY bm25(trechos) LIMIT ?", (fts, K)).fetchall()
        for posto, (h, idx, pg, texto) in enumerate(linhas, 1):
            i = "%s:%d" % (h, idx)
            pontos[i] = pontos.get(i, 0.0) + 1.0 / (RRF_K + posto)
            dados.setdefault(i, (h, int(pg), texto))

    melhor: dict[str, tuple[float, str]] = {}      # hash -> (pontuacao, id)
    for i, s in pontos.items():
        h = dados[i][0]
        if h not in melhor or s > melhor[h][0]:
            melhor[h] = (s, i)
    top = sorted(melhor.items(), key=lambda kv: -kv[1][0])[:max(1, n)]
    out = []
    for h, (s, i) in top:
        doc = con.execute("SELECT titulo, nome, caminho FROM docs WHERE hash=?", (h,)).fetchone() or ("", "", "")
        _, pg, texto = dados[i]
        out.append({"titulo": doc[0], "arquivo": doc[1], "pagina": pg, "pontuacao": round(s, 4),
                    "trecho": texto[:400] + ("..." if len(texto) > 400 else ""), "caminho": doc[2]})
    con.close()
    return out


def status(indice: Path | None = None) -> dict:
    """Progresso da ultima indexacao + contagens do indice."""
    indice = indice or INDICE
    st: dict = {}
    if (indice / "status.json").exists():
        try:
            st = json.loads((indice / "status.json").read_text(encoding="utf-8"))
        except ValueError:
            st = {"erro": "status.json ilegivel"}
    if (indice / "biblioteca.db").exists():
        con = _db(indice)
        st["docs_indexados"] = con.execute("SELECT COUNT(*) FROM docs WHERE erro IS NULL").fetchone()[0]
        st["docs_com_falha"] = con.execute("SELECT COUNT(*) FROM docs WHERE erro IS NOT NULL").fetchone()[0]
        st["docs_sem_texto"] = con.execute("SELECT COUNT(*) FROM docs WHERE erro IS NULL AND trechos=0").fetchone()[0]
        st["trechos"] = con.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
        con.close()
    else:
        st["docs_indexados"] = 0
    st["indice"] = str(indice)
    st["pdfs"] = str(PDFS)
    return st


def falhas(indice: Path | None = None) -> list[dict]:
    indice = indice or INDICE
    if not (indice / "biblioteca.db").exists():
        return []
    con = _db(indice)
    out = [{"arquivo": n, "erro": e} for n, e in
           con.execute("SELECT nome, erro FROM docs WHERE erro IS NOT NULL ORDER BY nome")]
    con.close()
    return out
