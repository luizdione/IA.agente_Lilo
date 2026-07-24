"""
Testes de shared/summarize.py (V20.1). Travam os bugs da auditoria: erro de
leitura virando "conteudo" destilado, guarda de binario morta, e max_chars sem
clamp. As funcoes que dependem do Ollama sao testadas com um cliente falso.
"""
from shared.summarize import (summarize_file, _looks_binary, _clip_head_tail,
                              _read_text)
from pathlib import Path


def test_looks_binary():
    assert _looks_binary(b"\x00\x01\x02texto") is True          # NUL
    assert _looks_binary(b"texto normal em ascii\n") is False
    assert _looks_binary(b"") is False


def test_read_text_binario_por_conteudo(tmp_path):
    # .txt (extensao "textual") mas com NUL -> deve ser barrado pelo sniff,
    # nao decodificado como mojibake latin-1.
    f = tmp_path / "fake.txt"
    f.write_bytes(b"\x00\x01\x02\x03binario disfarcado de txt")
    _, orig = _read_text(f)
    assert orig == -1


def test_clip_head_tail_preserva_extremos():
    txt = "INICIO" + ("x" * 5000) + "FIM"
    clip = _clip_head_tail(txt, 1000)
    assert clip.startswith("INICIO")
    assert clip.endswith("FIM")
    assert "meio omitido" in clip
    # texto curto passa intacto
    assert _clip_head_tail("abc", 1000) == "abc"


def test_arquivo_inexistente():
    assert "nao encontrado" in summarize_file("/nao/existe/x.log").lower()


def test_diretorio(tmp_path):
    assert "diretorio" in summarize_file(str(tmp_path)).lower()


def test_binario_nao_vira_resumo(tmp_path):
    f = tmp_path / "x.bam"
    f.write_bytes(b"BAM\x01\x00\x00\x00qualquer coisa")
    out = summarize_file(str(f))
    assert "binario" in out.lower() or "nao-textual" in out.lower()


def test_erro_de_leitura_nao_vira_conteudo(tmp_path, monkeypatch):
    # Se a leitura falhar, o resultado deve ser um ERRO explicito -- nunca um
    # resumo (que seria fabricado a partir da mensagem de erro).
    f = tmp_path / "x.txt"
    f.write_text("ok", encoding="utf-8")

    import shared.summarize as sm

    def _boom(_self_or_path):  # assinatura de open()
        raise PermissionError("negado")

    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(PermissionError("negado")))
    out = summarize_file(str(f))
    assert out.startswith("[summarize] Falha ao ler")


def test_max_chars_clamp_e_truncagem(tmp_path, monkeypatch):
    f = tmp_path / "grande.txt"
    f.write_text("conteudo cientifico valido. " * 100, encoding="utf-8")

    class _FakeClient:
        def chat(self, *a, **k):
            return "R" * 5000

    import shared.llm_client as llm
    monkeypatch.setattr(llm, "get_client", lambda: _FakeClient())

    # max_chars=0 -> saneado para o default (1200) e resumo truncado nesse teto
    out = summarize_file(str(f), max_chars=0)
    assert "truncado em 1200" in out
