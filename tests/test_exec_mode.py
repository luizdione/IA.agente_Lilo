"""tests/test_exec_mode.py — modos de execução (V14), offline."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _restore_mode():
    from shared import exec_mode as xm
    saved = xm.get_mode()
    yield
    xm.set_mode(saved)        # nunca vaza o modo entre testes


def test_auto_lets_everything_through():
    from shared import exec_mode as xm
    xm.set_mode("auto")
    for kind in ("write", "write_outside", "shell", "python"):
        assert xm.gate(kind, "x") is None


def test_plan_blocks_all_actions():
    from shared import exec_mode as xm
    xm.set_mode("plan")
    for kind in ("write", "shell", "python"):
        out = xm.gate(kind, "x")
        assert out and xm.is_block(out)


def test_ask_confirms_risk_and_grant_releases_once():
    from shared import exec_mode as xm
    xm.set_mode("ask")
    out = xm.gate("shell", "rm -rf /")
    assert out and xm.is_confirm(out)        # pediu confirmacao, nao executou
    xm.grant_once()
    assert xm.gate("shell", "rm -rf /") is None   # autorizado 1x
    assert xm.is_confirm(xm.gate("shell", "again"))  # grant foi consumido


def test_accept_edits_writes_but_confirms_shell():
    from shared import exec_mode as xm
    xm.set_mode("accept_edits")
    assert xm.gate("write", "file.md") is None       # edicao passa
    assert xm.is_confirm(xm.gate("shell", "ls"))     # shell confirma
    assert xm.is_confirm(xm.gate("python", "print(1)"))


def test_desktop_run_shell_respects_mode():
    from shared import exec_mode as xm
    from agents.desktop.agent import run_shell
    xm.set_mode("plan")
    assert xm.is_block(run_shell("echo oi"))         # nao executa
    xm.set_mode("ask")
    assert xm.is_confirm(run_shell("echo oi"))       # pede confirmacao
    xm.grant_once()
    assert "exit=" in run_shell("echo oi")           # confirmado -> executa
