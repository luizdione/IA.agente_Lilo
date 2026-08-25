"""Testes do contexto de projeto (F2)."""
from lilo import contexto


def test_le_key_files_em_ordem(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("regras do claude", encoding="utf-8")
    (tmp_path / "README.md").write_text("leia-me", encoding="utf-8")
    (tmp_path / "LILO.md").write_text("regras do lilo", encoding="utf-8")
    bloco = contexto.bloco_projeto(tmp_path)
    assert bloco.startswith(contexto.ROTULO)
    assert bloco.index("regras do lilo") < bloco.index("regras do claude")
    assert bloco.index("regras do claude") < bloco.index("leia-me")


def test_vazio_sem_arquivos(tmp_path):
    assert contexto.bloco_projeto(tmp_path) == ""


def test_trunca_no_teto(tmp_path):
    (tmp_path / "README.md").write_text("A" * 50_000, encoding="utf-8")
    bloco = contexto.bloco_projeto(tmp_path, max_chars=1000)
    assert len(bloco) < 1500
    assert "truncado" in bloco
