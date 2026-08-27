"""Testes da v13.7 — `lilo web` (chat no navegador, stdlib, mesmo portao).

Hermeticos: servidor real em porta EFEMERA (127.0.0.1:0) com FakeOllama
injetado no ClienteOllama — HTTP de verdade, zero rede externa. O fluxo de
confirmacao e provado de ponta a ponta: a thread da tarefa BLOQUEIA na
pendencia e o POST /api/confirmar libera (mesma pausa-no-ponto do terminal).
"""
from __future__ import annotations

import http.client
import json
import threading
import time

import pytest

from tests.conftest import FakeOllama, resposta_texto, resposta_tools
from lilo import web
from lilo.cliente import ClienteOllama


@pytest.fixture
def servidor(monkeypatch, tmp_path):
    """Sobe um `lilo web` de teste; devolve (porta, estado, fila_do_fake)."""
    monkeypatch.setenv("LILO_MODE", "ask")
    monkeypatch.setenv("LILO_SESSIONS_DB", str(tmp_path / "sessions.db"))
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "memoria.db"))
    monkeypatch.setenv("LILO_RESUMO", "0")
    monkeypatch.setenv("LILO_STREAM", "0")
    fake = FakeOllama([])
    srv = web.criar_servidor(porta=0, cliente=ClienteOllama(transport=fake))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield srv.server_address[1], srv.estado, fake
    srv.shutdown()
    srv.server_close()
    th.join(timeout=5)


def _req(porta: int, metodo: str, rota: str, corpo: dict | None = None):
    c = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
    c.request(metodo, rota,
              body=json.dumps(corpo) if corpo is not None else None)
    r = c.getresponse()
    dados = r.read().decode("utf-8")
    c.close()
    try:
        return r.status, json.loads(dados)
    except json.JSONDecodeError:
        return r.status, dados


def _esperar(cond, timeout=8.0):
    fim = time.time() + timeout
    while time.time() < fim:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_pagina_e_info(servidor):
    porta, estado, _ = servidor
    st, corpo = _req(porta, "GET", "/")
    assert st == 200 and "LILO" in corpo and "api/status" in corpo
    st, info = _req(porta, "GET", "/api/info")
    assert st == 200 and info["modo"] == "ask" and "versao" in info


def test_tarefa_so_texto_ate_resposta(servidor):
    porta, estado, fake = servidor
    fake.respostas.append(resposta_texto("ola do lilo web"))
    st, r = _req(porta, "POST", "/api/tarefa", {"tarefa": "diga ola"})
    assert st == 200 and r["ok"]
    assert _esperar(lambda: not estado.rodando)
    st, s = _req(porta, "GET", "/api/status")
    tipos = [h["t"] for h in s["historico"]]
    assert tipos[0] == "user" and "lilo" in tipos
    assert any("ola do lilo web" in h["texto"] for h in s["historico"])


def test_tarefa_vazia_e_ocupado(servidor):
    porta, estado, fake = servidor
    st, _ = _req(porta, "POST", "/api/tarefa", {"tarefa": "  "})
    assert st == 400
    # ocupa o servidor com uma tarefa que trava na confirmacao de shell
    fake.respostas.append(resposta_tools(("shell", {"comando": "echo oi"})))
    _req(porta, "POST", "/api/tarefa", {"tarefa": "rode echo"})
    assert _esperar(lambda: estado.pendente is not None)
    st, _ = _req(porta, "POST", "/api/tarefa", {"tarefa": "outra"})
    assert st == 409
    fake.respostas.append(resposta_texto("ok, nao rodei"))
    _req(porta, "POST", "/api/confirmar", {"resposta": "n"})
    assert _esperar(lambda: not estado.rodando)


def test_confirmacao_nega_e_loop_recebe_negado(servidor):
    porta, estado, fake = servidor
    fake.respostas.append(resposta_tools(("shell", {"comando": "rm x"})))
    fake.respostas.append(resposta_texto("entendido, nao executei"))
    _req(porta, "POST", "/api/tarefa", {"tarefa": "apague x"})
    assert _esperar(lambda: estado.pendente is not None)
    st, s = _req(porta, "GET", "/api/status")
    assert s["pendente"]["kind"] == "shell"
    assert "rm x" in s["pendente"]["preview"]
    st, r = _req(porta, "POST", "/api/confirmar", {"resposta": "n"})
    assert st == 200
    assert _esperar(lambda: not estado.rodando)
    # o resultado [NEGADO] voltou ao modelo na 2a chamada do fake
    msgs_2a = fake.chamadas[1][1]["messages"]
    assert any(m.get("role") == "tool" and "[NEGADO]" in str(m.get("content"))
               for m in msgs_2a)
    # e a recusa ficou visivel no historico da pagina
    assert any(h["t"] == "confirm" and "nao" in h["texto"]
               for h in estado.historico)


def test_confirmacao_sempre_registra_grant(servidor):
    porta, estado, fake = servidor
    fake.respostas.append(resposta_tools(("shell", {"comando": "echo oi"})))
    fake.respostas.append(resposta_texto("rodei"))
    _req(porta, "POST", "/api/tarefa", {"tarefa": "rode echo oi"})
    assert _esperar(lambda: estado.pendente is not None)
    _req(porta, "POST", "/api/confirmar", {"resposta": "t"})
    assert _esperar(lambda: not estado.rodando)
    assert estado.sessao.perms.grants_cmd  # grant escopado pelo hash do comando
    st, _ = _req(porta, "POST", "/api/confirmar", {"resposta": "s"})
    assert st == 409  # nada mais pendente


def test_modo_e_nova(servidor):
    porta, estado, fake = servidor
    st, r = _req(porta, "POST", "/api/modo", {"modo": "auto"})
    assert st == 200 and estado.sessao.perms.modo == "auto"
    st, _ = _req(porta, "POST", "/api/modo", {"modo": "turbo"})
    assert st == 400
    fake.respostas.append(resposta_texto("oi"))
    _req(porta, "POST", "/api/tarefa", {"tarefa": "oi"})
    assert _esperar(lambda: not estado.rodando)
    st, _ = _req(porta, "POST", "/api/nova", {})
    assert st == 200 and estado.historico == []
    assert estado.sessao.perms.modo == "ask"  # nova sessao volta ao LILO_MODE


def test_persistencia_compartilhada_com_terminal(servidor):
    porta, estado, fake = servidor
    fake.respostas.append(resposta_texto("salvo!"))
    _req(porta, "POST", "/api/tarefa", {"tarefa": "memorize isso"})
    assert _esperar(lambda: not estado.rodando)
    from lilo import sessoes
    cid = estado.sessao.chat_id
    assert cid, "conversa do navegador deve ganhar chat_id persistido"
    msgs = sessoes.carregar(cid)
    assert any(m["role"] == "user" and "memorize isso" in str(m["content"])
               for m in msgs)


def test_rota_desconhecida_404(servidor):
    porta, _, _ = servidor
    assert _req(porta, "GET", "/api/nada")[0] == 404
    assert _req(porta, "POST", "/api/nada", {})[0] == 404
