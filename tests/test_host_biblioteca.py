"""Biblioteca de PDFs: fatiamento, indexacao incremental e busca hibrida (embedder falso,
sem baixar nem carregar o bge-m3)."""
from __future__ import annotations

import os
import re
import time
import zlib

import numpy as np
import pytest

from lilo_host import biblioteca as B


class EmbFalso:
    """Saco de palavras hasheado em 64 dimensoes: busca 'semantica' = sobreposicao lexical."""
    dispositivo = "cpu"

    def codificar(self, textos):
        out = np.zeros((len(textos), 64), dtype=np.float32)
        for i, t in enumerate(textos):
            for tok in re.findall(r"\w+", t.lower()):
                out[i, zlib.crc32(tok.encode()) % 64] += 1.0
            n = float(np.linalg.norm(out[i]))
            out[i] /= n or 1.0
        return out


def _pdf(caminho, paginas):
    fitz = pytest.importorskip("fitz")
    d = fitz.open()
    for texto in paginas:
        pg = d.new_page()
        y = 72
        for linha in texto.split("\n"):
            pg.insert_text((72, y), linha)
            y += 14
    d.save(str(caminho))
    d.close()


def test_fatiar_janelas_e_paginas():
    pags = ["", "x" * 50, ("Frase um. " * 60).strip(), "Pagina quatro curta mas util o bastante para um trecho. " * 2]
    pedacos = B.fatiar(pags, tamanho=200, sobre=40)
    paginas = {pg for pg, _ in pedacos}
    assert paginas == {3, 4}                       # vazia e curta demais foram puladas
    assert all(len(t) >= B.TRECHO_MIN for _, t in pedacos)
    assert all(len(t) <= 200 for _, t in pedacos)
    terceira = [t for pg, t in pedacos if pg == 3]
    assert len(terceira) >= 3 and terceira[0].endswith(".")   # corte em fim de frase


@pytest.fixture
def lib(tmp_path):
    pdfs, indice = tmp_path / "pdfs", tmp_path / "indice"
    pdfs.mkdir()
    _pdf(pdfs / "mito.pdf", ["Mitochondrial respiration and ATP synthesis in muscle cells.\n" * 8])
    _pdf(pdfs / "ns1.pdf", ["The flavivirus NS1 protein binds the plasma membrane of infected cells.\n" * 8,
                            "NS1 secretion correlates with dengue severity in patients.\n" * 8])
    _pdf(pdfs / "vina.pdf", ["AutoDock Vina docking scores for kinase inhibitors were compared.\n" * 8])
    return pdfs, indice


def test_indexar_incremental_e_buscar(lib):
    pdfs, indice = lib
    emb = EmbFalso()
    st = B.indexar(pdfs, indice, embedder=emb, log=lambda *a: None)
    assert (st["total"], st["novos"], st["pulados"], st["falhas"]) == (3, 3, 0, 0)
    assert (indice / "status.json").exists() and (indice / "biblioteca.db").exists()
    s = B.status(indice)
    assert s["docs_indexados"] == 3 and s["trechos"] >= 4 and s["docs_com_falha"] == 0

    r = B.buscar("flavivirus NS1 membrane", n=3, indice=indice, embedder=emb)
    assert isinstance(r, list) and r[0]["arquivo"] == "ns1.pdf" and r[0]["pagina"] == 1
    assert "NS1" in r[0]["trecho"] and r[0]["titulo"].startswith("The flavivirus NS1")
    assert len({x["arquivo"] for x in r}) == len(r)        # um resultado por documento
    r2 = B.buscar("dengue severity patients", n=1, indice=indice, embedder=emb)
    assert r2[0]["arquivo"] == "ns1.pdf" and r2[0]["pagina"] == 2
    assert B.buscar("docking kinase", n=1, indice=indice, embedder=emb)[0]["arquivo"] == "vina.pdf"
    assert B.buscar("   ", indice=indice, embedder=emb) == []

    # 2a rodada: nada muda, nada e reindexado (nem re-hash)
    st2 = B.indexar(pdfs, indice, embedder=emb, log=lambda *a: None)
    assert (st2["novos"], st2["pulados"]) == (0, 3)

    # PDF alterado: so ele volta; o indice continua com 3 docs e sem trechos orfaos
    time.sleep(1.1)
    _pdf(pdfs / "mito.pdf", ["Mitochondrial respiration and ATP synthesis in muscle cells.\n" * 8,
                             "A new page about oxidative phosphorylation efficiency.\n" * 8])
    st3 = B.indexar(pdfs, indice, embedder=emb, log=lambda *a: None)
    assert (st3["novos"], st3["pulados"]) == (1, 2)
    s3 = B.status(indice)
    assert s3["docs_indexados"] == 3
    assert B.buscar("oxidative phosphorylation", n=1, indice=indice, embedder=emb)[0]["pagina"] == 2
    con = B._db(indice)
    assert con.execute("SELECT COUNT(DISTINCT hash) FROM trechos").fetchone()[0] == 3
    assert B._colecao(indice).count() == con.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
    con.close()


def test_falha_isolada_e_limite(lib):
    pdfs, indice = lib
    (pdfs / "quebrado.pdf").write_bytes(b"%PDF-1.4 nada aqui")
    st = B.indexar(pdfs, indice, embedder=EmbFalso(), log=lambda *a: None)
    assert st["falhas"] == 1 and st["novos"] == 3
    f = B.falhas(indice)
    assert len(f) == 1 and f[0]["arquivo"] == "quebrado.pdf"
    st2 = B.indexar(pdfs, indice, embedder=EmbFalso(), limite=2, log=lambda *a: None)
    assert st2["total"] == 2


def test_buscar_sem_indice(tmp_path):
    assert B.buscar("x", indice=tmp_path / "nada").startswith("[ERRO]")
    assert B.status(tmp_path / "nada")["docs_indexados"] == 0
