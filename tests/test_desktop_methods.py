"""tests/test_desktop_methods.py — V18.5: regressao do crash do Explorer.

O dashboard (_render_villa_project_explorer) chama _desktop.fs_list/fs_read/
fs_write como METODOS; ate a V18.5 eram so funcoes de modulo ->
AttributeError. Aqui garantimos que os delegadores existem e delegam de fato
(respeitando a allow-list, apontada p/ um tmp_path via LILO_DESKTOP_ALLOW).
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def desktop(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_DESKTOP_ALLOW", str(tmp_path))
    import agents.desktop.agent as mod
    importlib.reload(mod)  # relê a allow-list do ambiente
    return mod.DesktopAgent()


def test_metodos_delegadores_existem(desktop):
    for m in ("fs_read", "fs_write", "fs_list", "fs_stat", "fs_search",
              "fs_move", "run_shell", "run_python"):
        assert callable(getattr(desktop, m)), f"faltou metodo {m}"


def test_fs_list_como_metodo_nao_estoura(desktop, tmp_path):
    (tmp_path / "a.txt").write_text("oi", encoding="utf-8")
    # a chamada exata que o Explorer faz (keyword args)
    out = desktop.fs_list(str(tmp_path), glob="*", recursive=False, limit=500)
    assert isinstance(out, str) and "a.txt" in out


def test_fs_read_write_roundtrip_como_metodo(desktop, tmp_path):
    alvo = tmp_path / "nota.txt"
    desktop.fs_write(str(alvo), "conteudo de teste")
    assert "conteudo de teste" in desktop.fs_read(str(alvo))
