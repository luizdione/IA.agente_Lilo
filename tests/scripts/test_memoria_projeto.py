"""tests/scripts/test_memoria_projeto.py — V18.10: gerente de memoria.

Offline e hermetico: refresh() num tmp_path (cria do template e preserva as
secoes MANUAL), sem rodar o diagnostico (run_diag=False). O parser de
CHANGELOG e o substituidor de blocos sao testados direto.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import memoria_projeto as mp  # noqa: E402


def test_cria_do_template_e_preenche_auto(tmp_path):
    ctx = tmp_path / "CONTEXT.md"
    texto = mp.refresh(path=ctx, run_diag=False)
    assert ctx.exists()
    assert "<!-- AUTO:estado -->" in texto and "**Versao:**" in texto
    assert "<!-- AUTO:entregas -->" in texto
    # secoes manuais do template presentes
    assert "## Pendencias (MANUAL)" in texto


def test_preserva_secoes_manuais(tmp_path):
    ctx = tmp_path / "CONTEXT.md"
    mp.refresh(path=ctx, run_diag=False)
    marcado = ctx.read_text(encoding="utf-8").replace(
        "## Pendencias (MANUAL)\n\n(vazio)",
        "## Pendencias (MANUAL)\n\n- [ ] item que NAO pode sumir")
    ctx.write_text(marcado, encoding="utf-8")
    texto2 = mp.refresh(path=ctx, run_diag=False)
    assert "item que NAO pode sumir" in texto2


def test_substitui_bloco_erro_sem_marcador():
    try:
        mp._substitui_bloco("sem marcadores", "estado", "x")
        assert False, "deveria levantar ValueError"
    except ValueError as e:
        assert "AUTO:estado" in str(e)


def test_entregas_le_changelog_real():
    md = mp._entregas_md(max_itens=2)
    # o CHANGELOG real do repo tem entradas v12.x no topo
    assert md.startswith("- v12.")
