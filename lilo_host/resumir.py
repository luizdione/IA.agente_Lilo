"""Leitura de arquivos e resumo pelo `lilo` (grupo conhecimento).

- `ler_pdf`: paginado, herdado da v13 (`lilo/tools.py:_ler_pdf`), PyMuPDF.
- `ler_texto`: texto/CSV/log/MD/DOCX/PDF com teto de leitura e recorte inicio+fim
  (sniff de binario herdado de `arch-v11:shared/summarize.py`).
- `resumir_arquivo`: `ler_texto` + uma chamada ao `lilo` (think desligado, sem opcoes
  de runner). Respeita o interruptor de GPU: reservada = nao chama o modelo.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from .comum import MODELO, OLLAMA, erro, gpu_reservada, recortar, resolver

PDF_MAX_PAGINAS = 40
PDF_MAX_CHARS = 24000
LER_MAX_BYTES = 2_000_000
EXT_BINARIAS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".zip", ".gz",
                ".xz", ".7z", ".rar", ".exe", ".dll", ".so", ".pyc", ".parquet", ".npz",
                ".npy", ".h5", ".hdf5", ".bam", ".cram", ".pzf", ".pzfx", ".dna", ".xlsx"}
_TEXTO = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D, 0x0C, 0x08, 0x1B}

_SISTEMA = ("Voce resume arquivos para um pesquisador. Responda em portugues, de forma "
            "direta, so com o que esta no texto; numeros e nomes exatos. Sem introducao.")


def _parece_binario(raw: bytes) -> bool:
    cabeca = raw[:8192]
    if not cabeca:
        return False
    if b"\x00" in cabeca:
        return True
    nao_texto = sum(1 for b in cabeca if b < 0x80 and b not in _TEXTO)
    return nao_texto / len(cabeca) > 0.30


def ler_pdf(caminho: str, pagina_inicial: int = 1, paginas: int = PDF_MAX_PAGINAS) -> str:
    """Texto de um PDF, por janela de paginas (max 40 por chamada, 24k caracteres)."""
    p = resolver(caminho)
    if not p.exists():
        return erro("arquivo nao existe: %s" % p)
    if p.suffix.lower() != ".pdf":
        return erro("%s nao e um PDF; use ler_texto" % p.name)
    import fitz  # PyMuPDF
    inicial = max(1, int(pagina_inicial or 1))
    quantas = max(1, min(PDF_MAX_PAGINAS, int(paginas or PDF_MAX_PAGINAS)))
    try:
        doc = fitz.open(str(p))
    except Exception as e:  # noqa: BLE001 — PDF corrompido/cifrado volta ao modelo
        return erro("PDF ilegivel (%s): %s" % (type(e).__name__, e))
    try:
        total = doc.page_count
        if inicial > total:
            return erro("pagina_inicial=%d, mas o PDF tem %d pagina(s)" % (inicial, total))
        fim = min(total, inicial + quantas - 1)
        partes, chars, ultima = [], 0, inicial - 1
        for i in range(inicial - 1, fim):
            texto = doc[i].get_text("text").strip()
            bloco = "--- pagina %d ---\n%s" % (i + 1, texto or "(sem texto: pagina so de imagem?)")
            partes.append(bloco)
            chars += len(bloco)
            ultima = i + 1
            if chars >= PDF_MAX_CHARS and ultima < fim:
                break
        corpo = ["[PDF %s: %d paginas; exibindo %d-%d]" % (p.name, total, inicial, ultima)] + partes
        if total - ultima > 0:
            corpo.append("... (+%d paginas; use pagina_inicial=%d)" % (total - ultima, ultima + 1))
        return "\n".join(corpo)
    finally:
        doc.close()


def _texto_docx(p: Path) -> str:
    from .docx import ler as docx_ler
    return docx_ler(str(p))


def ler_texto(caminho: str, max_chars: int = 12000) -> str:
    """Conteudo textual de um arquivo (txt, md, csv, log, json, py, R, docx, pdf...),
    recortado em inicio+fim se passar de max_chars."""
    p = resolver(caminho)
    if not p.is_file():
        return erro("arquivo nao existe: %s" % p)
    ext = p.suffix.lower()
    if ext == ".pdf":
        import fitz
        try:
            with fitz.open(str(p)) as doc:
                texto = "\n".join(pg.get_text("text") for pg in doc)
        except Exception as e:  # noqa: BLE001
            return erro("PDF ilegivel: %s" % e)
        return recortar(texto, max_chars)
    if ext == ".docx":
        return recortar(_texto_docx(p), max_chars)
    if ext in EXT_BINARIAS:
        return erro("%s e binario (%s); use a skill perfil_dados para dados" % (p.name, ext))
    try:
        raw = p.open("rb").read(LER_MAX_BYTES + 1)
    except OSError as e:
        return erro("leitura: %s" % e)
    if _parece_binario(raw):
        return erro("%s parece binario" % p.name)
    raw = raw[:LER_MAX_BYTES]
    try:
        texto = raw.decode("utf-8")
    except UnicodeDecodeError:
        texto = raw.decode("latin-1")
    return recortar(texto, max_chars)


def _chamar_lilo(prompt: str, sistema: str = _SISTEMA, timeout: float = 180.0) -> str:
    corpo = {"model": MODELO, "stream": False, "think": False,
             "messages": [{"role": "system", "content": sistema},
                          {"role": "user", "content": prompt}]}
    r = httpx.post(f"{OLLAMA}/api/chat", json=corpo, timeout=timeout)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def resumir_arquivo(caminho: str, pergunta: str = "", max_chars: int = 1200) -> str:
    """Resumo de um arquivo pelo `lilo` (ate ~12k caracteres lidos), opcionalmente
    guiado por uma pergunta. Nao roda com a GPU reservada."""
    motivo = gpu_reservada()
    if motivo:
        return erro("GPU reservada (%s): o modelo nao sera carregado. Use ler_texto." % motivo)
    texto = ler_texto(caminho, max_chars=12000)
    if texto.startswith("[ERRO]"):
        return texto
    pedido = ("Resuma o arquivo abaixo em ate %d caracteres" % max_chars
              + (", respondendo a: %s" % pergunta if pergunta else "")
              + ".\n\n=== ARQUIVO %s ===\n%s" % (resolver(caminho).name, texto))
    try:
        return _chamar_lilo(pedido)
    except httpx.HTTPError as e:
        return erro("Ollama indisponivel: %s" % e)
