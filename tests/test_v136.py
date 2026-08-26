"""Testes da v13.6 — tool ler_pdf (primeira tool cientifica; PyMuPDF opcional).

Duas familias: (a) hermeticos puros — registro, validacao de argumentos e o
caminho SEM PyMuPDF (via monkeypatch de _importar_fitz), rodam em qualquer CI;
(b) com PyMuPDF real — geram o proprio PDF com fitz e pulam limpo
(importorskip) se o pacote opcional nao estiver instalado.
"""
import pytest

from lilo import mcp_servidor, tools
from lilo.portao import Permissoes


def _exec(nome: str, args: dict, modo: str = "ask") -> str:
    # confirmar devolve "n": se o portao perguntar, o teste ve [NEGADO] —
    # prova de que ler_pdf e leitura LIVRE (kind None) em qualquer modo.
    return tools.executar_tool(nome, args, Permissoes(modo=modo),
                               lambda kind, preview: "n")


# --- hermeticos (sem PyMuPDF) -----------------------------------------------
def test_ler_pdf_registrada_como_leitura_livre():
    assert "ler_pdf" in tools.TOOLS
    assert tools.TOOLS["ler_pdf"].classificar({"caminho": "x.pdf"}) == (None, None)
    assert any(s["function"]["name"] == "ler_pdf" for s in tools.SCHEMAS)


def test_ler_pdf_exposta_no_mcp_serve():
    assert "ler_pdf" in mcp_servidor.WRAPPERS
    assert len(mcp_servidor.WRAPPERS) == 10


def test_ler_pdf_arquivo_inexistente(tmp_path):
    saida = _exec("ler_pdf", {"caminho": str(tmp_path / "nada.pdf")})
    assert saida.startswith("[ERRO]")


def test_ler_pdf_recusa_nao_pdf(tmp_path):
    arq = tmp_path / "nota.txt"
    arq.write_text("oi", encoding="utf-8")
    saida = _exec("ler_pdf", {"caminho": str(arq)})
    assert "nao e um PDF" in saida


def test_ler_pdf_sem_pymupdf_instrui_instalacao(tmp_path, monkeypatch):
    arq = tmp_path / "artigo.pdf"
    arq.write_bytes(b"%PDF-1.4 qualquer")

    def _sem_fitz():
        raise ImportError("No module named 'fitz'")

    monkeypatch.setattr(tools, "_importar_fitz", _sem_fitz)
    saida = _exec("ler_pdf", {"caminho": str(arq)})
    assert "pip install PyMuPDF" in saida


# --- com PyMuPDF real (pula limpo se o opcional nao estiver instalado) ------
fitz = pytest.importorskip("fitz", reason="PyMuPDF (opcional) nao instalado")


def _gerar_pdf(caminho, textos):
    doc = fitz.open()
    for texto in textos:
        doc.new_page().insert_text((72, 72), texto)
    doc.save(str(caminho))
    doc.close()


def test_ler_pdf_extrai_texto_paginado(tmp_path):
    pdf = tmp_path / "artigo.pdf"
    _gerar_pdf(pdf, ["RNA-seq de cana-de-acucar", "metodos: DESeq2",
                     "conclusao: expressao diferencial"])
    saida = _exec("ler_pdf", {"caminho": str(pdf)})
    assert "[PDF artigo.pdf — 3 paginas; exibindo 1-3]" in saida
    assert "--- pagina 1 ---" in saida and "RNA-seq" in saida
    assert "DESeq2" in saida and "expressao diferencial" in saida
    assert "use pagina_inicial" not in saida  # coube inteiro: sem dica


def test_ler_pdf_pagina_inicial_e_limite(tmp_path):
    pdf = tmp_path / "longo.pdf"
    _gerar_pdf(pdf, ["um", "dois", "tres", "quatro"])
    saida = _exec("ler_pdf",
                  {"caminho": str(pdf), "pagina_inicial": 2, "paginas": 2})
    assert "exibindo 2-3" in saida
    assert "--- pagina 2 ---" in saida and "--- pagina 3 ---" in saida
    assert "--- pagina 1 ---" not in saida and "--- pagina 4 ---" not in saida
    assert "(+1 paginas — use pagina_inicial=4)" in saida


def test_ler_pdf_pagina_inicial_alem_do_fim(tmp_path):
    pdf = tmp_path / "curto.pdf"
    _gerar_pdf(pdf, ["so uma pagina"])
    saida = _exec("ler_pdf", {"caminho": str(pdf), "pagina_inicial": 9})
    assert saida.startswith("[ERRO]") and "1 pagina" in saida


def test_ler_pdf_corrompido_vira_erro_instrutivo(tmp_path):
    pdf = tmp_path / "quebrado.pdf"
    pdf.write_bytes(b"%PDF-1.4 lixo sem estrutura")
    saida = _exec("ler_pdf", {"caminho": str(pdf)})
    assert saida.startswith("[ERRO]")


def test_ler_pdf_corta_no_teto_de_chars_com_dica(tmp_path):
    pdf = tmp_path / "denso.pdf"
    # 40 linhas de ~66 chars por pagina (~2.7k) x 12 paginas (~32k) -> o teto
    # de 24k corta antes da ultima pagina
    linhas = "\n".join(("linha %02d | " % j) * 6 for j in range(40))
    _gerar_pdf(pdf, ["pagina %02d\n%s" % (i, linhas) for i in range(12)])
    saida = _exec("ler_pdf", {"caminho": str(pdf)})
    assert len(saida) < tools.LIMITE_RESULTADO  # nunca depende do truncador global
    assert "use pagina_inicial=" in saida       # dica de continuacao preservada


def test_ler_pdf_via_mcp_serve_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_MCP_SERVE_MODE", "accept_edits")
    pdf = tmp_path / "mcp.pdf"
    _gerar_pdf(pdf, ["conteudo servido via MCP"])
    saida = mcp_servidor.ler_pdf(str(pdf))
    assert "conteudo servido via MCP" in saida
