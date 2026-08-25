"""Smoke minimo do repo pos-demolicao (v13 F0).

Garante que a suite nunca colete 0 testes — pytest retorna exit code 5
nesse caso e o scripts/check.py (e o CI) ficariam vermelhos. Substituido
por testes reais conforme o pacote lilo/ ganha modulos (F1+).
"""


def test_python_ok():
    assert True
