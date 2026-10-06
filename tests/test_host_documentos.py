"""Ponte lilo-host: leitura de texto/PDF, DOCX ida e volta e resumo (modelo simulado)."""
from __future__ import annotations

import pytest

from lilo_host import docx, resumir


def test_ler_texto_e_binario(tmp_path):
    t = tmp_path / "a.txt"
    t.write_text("linha 1\nlinha 2\n" * 10, encoding="utf-8")
    assert "linha 1" in resumir.ler_texto(str(t))
    grande = tmp_path / "g.log"
    grande.write_text("x" * 50000, encoding="utf-8")
    r = resumir.ler_texto(str(grande), max_chars=1000)
    assert "meio omitido" in r and len(r) < 1300
    b = tmp_path / "b.dat"
    b.write_bytes(b"\x00\x01\x02" * 100)
    assert resumir.ler_texto(str(b)).startswith("[ERRO]")
    assert resumir.ler_texto(str(tmp_path / "img.png")).startswith("[ERRO]")
    assert resumir.ler_texto(str(tmp_path / "nao.txt")).startswith("[ERRO]")


def test_ler_pdf_paginado(tmp_path):
    fitz = pytest.importorskip("fitz")
    p = tmp_path / "t.pdf"
    d = fitz.open()
    for i in range(3):
        d.new_page().insert_text((72, 72), "Pagina numero %d do teste" % (i + 1))
    d.save(str(p))
    d.close()
    r = resumir.ler_pdf(str(p), pagina_inicial=2, paginas=1)
    assert "3 paginas; exibindo 2-2" in r and "Pagina numero 2" in r and "pagina_inicial=3" in r
    assert resumir.ler_pdf(str(p), pagina_inicial=9).startswith("[ERRO]")
    assert resumir.ler_pdf(str(tmp_path / "x.txt")).startswith("[ERRO]")
    assert "Pagina numero 3" in resumir.ler_texto(str(p))


def test_docx_ida_e_volta(tmp_path):
    md = ("# Relatorio\n\nParagrafo um,\ncontinuado.\n\n## Metodos\n- item a\n- item b\n\n"
          "| grupo | n |\n|---|---|\n| A | 10 |\n| B | 12 |\n")
    alvo = tmp_path / "rel.docx"
    r = docx.escrever(str(alvo), md, titulo="Teste")
    assert r.startswith("gravado") and alvo.exists()
    t = docx.ler(str(alvo))
    assert "# Teste" in t and "# Relatorio" in t and "## Metodos" in t
    assert "Paragrafo um, continuado." in t and "- item a" in t
    assert "| grupo | n |" in t and "| B | 12 |" in t
    assert docx.escrever(str(tmp_path / "x.txt"), "a").startswith("[ERRO]")
    assert docx.ler(str(tmp_path / "nao.docx")).startswith("[ERRO]")


def test_resumir_respeita_gpu_e_chama_modelo(tmp_path, monkeypatch):
    t = tmp_path / "a.md"
    t.write_text("# Titulo\nTexto para resumir.", encoding="utf-8")
    monkeypatch.setattr(resumir, "gpu_reservada", lambda: "MD em andamento")
    assert "GPU reservada" in resumir.resumir_arquivo(str(t))
    monkeypatch.setattr(resumir, "gpu_reservada", lambda: None)
    visto = {}

    def falso(prompt, sistema=resumir._SISTEMA, timeout=180.0):
        visto["prompt"] = prompt
        return "RESUMO-OK"

    monkeypatch.setattr(resumir, "_chamar_lilo", falso)
    assert resumir.resumir_arquivo(str(t), pergunta="qual o titulo?") == "RESUMO-OK"
    assert "qual o titulo?" in visto["prompt"] and "Texto para resumir" in visto["prompt"]
    assert resumir.resumir_arquivo(str(tmp_path / "nao.md")).startswith("[ERRO]")
