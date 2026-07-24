"""Testes de shared/exec_env.py (ambientes de execução: conda + WSL).

Os testes herméticos (env_info/list/run self) rodam sempre e são rápidos. A
execução REAL num env conda é opcional (LILO_TEST_EXEC=1) para não pagar o
cold-start do `conda run` no check.py.
"""
from __future__ import annotations

import os
import pytest

from shared import exec_env as ee


def test_env_info_shape():
    info = ee.env_info()
    for k in ("conda_base", "conda_found", "conda_envs", "default_py_env",
              "wsl_distros", "lilo_python"):
        assert k in info
    assert isinstance(info["conda_envs"], list)
    assert isinstance(info["wsl_distros"], list)
    assert info["default_py_env"] == ee.default_py_env()


def test_list_conda_envs_is_list():
    envs = ee.list_conda_envs()
    assert isinstance(envs, list)


def test_run_python_self_executa():
    # env='self' -> Python do próprio LILO (sem depender de conda). Determinístico.
    out = ee.run_python("print(6*7)", env="self", timeout=30)
    assert "42" in out
    assert "[exit=0]" in out


def test_run_python_env_default_configuravel(monkeypatch):
    monkeypatch.setenv("LILO_PY_ENV", "meu_env_xyz")
    assert ee.default_py_env() == "meu_env_xyz"


def test_conda_exe_nao_crasha():
    # Pode ser None (sem conda) ou um caminho; nunca lança.
    exe = ee.conda_exe.__wrapped__() if hasattr(ee.conda_exe, "__wrapped__") else ee.conda_exe()
    assert exe is None or isinstance(exe, str)


@pytest.mark.skipif(not os.getenv("LILO_TEST_EXEC"),
                    reason="execução real no conda (cold-start); ligue com LILO_TEST_EXEC=1")
def test_run_python_datascience_real():
    out = ee.run_python("import numpy as np; print('NUMPY', np.__version__)",
                        env="datascience", timeout=120)
    assert "NUMPY" in out
    assert "[exit=0]" in out
