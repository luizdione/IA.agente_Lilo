"""tests/test_skillsmith.py — SkillSmithAgent (V13.4), offline e seguro.

Testa helpers puros e as GUARDAS (nome invalido / agente existente) que NAO
escrevem em agents/. A geracao real de scaffold foi validada e2e manualmente.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def smith():
    from agents.skillsmith.agent import SkillSmithAgent
    return SkillSmithAgent()


@pytest.mark.parametrize("name,ok", [
    ("foo_bar", True), ("paper2", True),
    ("1foo", False), ("Foo", False), ("def", False), ("", False),
    ("with-dash", False),
])
def test_valid_name(smith, name, ok):
    assert smith._valid_name(name) is ok


@pytest.mark.parametrize("name,cls", [
    ("foo", "FooAgent"), ("foo_bar", "FooBarAgent"),
    ("data_viz", "DataVizAgent"),
])
def test_class_name(smith, name, cls):
    assert smith._class_name(name) == cls


def test_scaffold_rejects_invalid_name(smith):
    out = smith._scaffold("1bad", "x", [], [])
    assert "invalido" in out.lower()


def test_scaffold_refuses_existing_agent(smith):
    # V18 QW1: usava 'paper', que NUNCA foi commitado (existe so na maquina de
    # origem) -- em checkout limpo o teste nao so falhava como CRIAVA
    # agents/paper/ de verdade (poluia o repo e fazia a suite do paper rodar
    # contra o stub na rodada seguinte). 'gateway' esta versionado no repo,
    # entao a guarda anti-sobrescrita e exercida em qualquer maquina.
    out = smith._scaffold("gateway", "x", [], [])
    assert "ja existe" in out.lower()


def test_tools_exposed(smith):
    assert {"propose_agent", "create_agent_scaffold"} == \
        {t["name"] for t in smith.get_tools()}
