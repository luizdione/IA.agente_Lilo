"""Testes das sessoes persistentes (F4) — SQLite em tmp_path."""
import sqlite3

import pytest

from lilo import sessoes


@pytest.fixture(autouse=True)
def _db_isolado(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_SESSIONS_DB", str(tmp_path / "sessions.db"))


MSGS = [
    {"role": "system", "content": "s"},
    {"role": "user", "content": "conserte o bug"},
    {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "ler", "arguments": {"caminho": "a.py"}}}]},
    {"role": "tool", "tool_name": "ler", "content": "1→x = 1"},
    {"role": "assistant", "content": "feito"},
]


def test_gravar_e_reidratar_fielmente():
    cid = sessoes.nova_sessao(cwd="/proj")
    sessoes.gravar(cid, MSGS)
    de_volta = sessoes.carregar(cid)
    assert de_volta == MSGS  # tool_calls e tool_name sobrevivem redondos


def test_wal_ativo(tmp_path):
    sessoes.nova_sessao()
    con = sqlite3.connect(str(tmp_path / "sessions.db"))
    modo = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.close()
    assert modo.lower() == "wal"


def test_ultima_sessao_e_retomada():
    assert sessoes.carregar_ultima() is None  # DB vazio
    c1 = sessoes.nova_sessao()
    sessoes.gravar(c1, MSGS[:2])
    c2 = sessoes.nova_sessao()
    sessoes.gravar(c2, MSGS)  # mais recente
    assert sessoes.ultima_sessao() == c2
    assert sessoes.carregar_ultima() == MSGS


def test_gravar_substitui_e_titula():
    cid = sessoes.nova_sessao()
    sessoes.gravar(cid, MSGS[:2])
    sessoes.gravar(cid, MSGS)  # regrava a cada iteracao — sem duplicar
    assert len(sessoes.carregar(cid)) == len(MSGS)
    con = sqlite3.connect(str(sessoes.config.sessions_db()))
    titulo = con.execute("SELECT titulo FROM chats WHERE id=?",
                         (cid,)).fetchone()[0]
    con.close()
    assert titulo == "conserte o bug"


def test_persistencia_por_iteracao_sobrevive_a_interrupcao():
    """Simula kill no meio: a ultima gravacao integral e o que fica."""
    cid = sessoes.nova_sessao()
    sessoes.gravar(cid, MSGS[:4])  # iteracao 1 gravada
    # 'kill' antes da iteracao 2: nada mais e gravado
    assert sessoes.carregar(cid) == MSGS[:4]
