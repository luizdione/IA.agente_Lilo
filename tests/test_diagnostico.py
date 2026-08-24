"""tests/test_diagnostico.py — V18.2: smoke da auditoria /diagnostico_lilo.

Roda o script em modo rapido e offline (--fast --no-runtime: sem pytest
aninhado, sem rede) e valida o contrato: relatorio compacto no stdout, secoes
esperadas presentes e exit code coerente com a escala P0/P1.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_diagnostico_roda_offline_e_respeita_contrato():
    r = subprocess.run(
        [sys.executable, "scripts/diagnostico_lilo.py", "--fast",
         "--no-runtime"],
        cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert r.returncode in (0, 1, 2)
    out = r.stdout
    assert "DIAGNOSTICO LILO" in out
    assert "Resumo:" in out
    for secao in ("## codigo", "## fiacao", "## envs", "## docs"):
        assert secao in out
    # A varredura de fiacao deve cobrir o registro de agentes (classe de bug
    # "paper fantasma"): ou o agente importa (OK) ou e sinalizado.
    assert "B-REG" in out
