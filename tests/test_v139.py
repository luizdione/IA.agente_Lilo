"""Testes da v13.9 — diagnostico da ponte MCP + stdout limpo no servidor.

A v13.8 falhou na maquina do dono por causa da ORDEM dos argumentos do
`claude mcp add` (a doc exige uma opcao entre `--env` e o nome do servidor)
e a mensagem util se perdeu. Aqui travamos: (a) as partes puras do
handshake, (b) a forma do comando gravado no script de conexao, (c) a
promessa de que o `mcp-serve` nao escreve NADA em stdout antes do protocolo.
"""
from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from lilo import mcp_servidor
from scripts import diagnosticar_mcp as diag

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT_PS1 = RAIZ / "scripts" / "conectar_claude_code.ps1"


# --- partes puras do handshake ----------------------------------------------
def test_frame_initialize_e_jsonrpc_valido():
    msg = json.loads(diag.frame_initialize())
    assert msg["jsonrpc"] == "2.0" and msg["method"] == "initialize"
    assert msg["id"] == 1
    assert msg["params"]["protocolVersion"] == diag.PROTOCOLO
    assert msg["params"]["clientInfo"]["name"]
    assert "\n" not in diag.frame_initialize()  # uma linha = um frame


def test_interpretar_resposta_ok():
    linha = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
        "protocolVersion": diag.PROTOCOLO,
        "serverInfo": {"name": "lilo", "version": "1"}}})
    ok, explicacao = diag.interpretar_resposta(linha)
    assert ok and "lilo" in explicacao


def test_interpretar_resposta_vazia_e_erro():
    ok, explicacao = diag.interpretar_resposta("")
    assert not ok and "nao respondeu" in explicacao
    ok, explicacao = diag.interpretar_resposta(
        json.dumps({"jsonrpc": "2.0", "id": 1,
                    "error": {"code": -32601, "message": "sem metodo"}}))
    assert not ok and "sem metodo" in explicacao


def test_interpretar_resposta_stdout_sujo():
    """O modo de falha classico: algo imprimiu no canal do protocolo."""
    ok, explicacao = diag.interpretar_resposta("Bem-vindo ao LILO!")
    assert not ok and "corrompeu o protocolo" in explicacao


def test_interpretar_resposta_sem_result():
    ok, explicacao = diag.interpretar_resposta(json.dumps({"jsonrpc": "2.0"}))
    assert not ok and "result" in explicacao


# --- o comando gravado pelo script de conexao -------------------------------
def test_conectar_usa_a_ordem_documentada_do_claude_mcp_add():
    """Regressao da causa-raiz: `--env` NAO pode encostar no nome do servidor
    (a doc le o nome como mais um par de variavel e o add falha)."""
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    # junta as continuacoes de linha (`) para inspecionar o comando inteiro
    comando = re.sub(r"`\s*\n\s*", " ", texto)
    m = re.search(r"mcp add (.+?) 2>&1", comando, re.S)
    assert m, "comando `claude mcp add` nao encontrado no script"
    args = m.group(1).split()
    i_env, i_nome = args.index("--env"), args.index("lilo")
    assert i_env < i_nome, "--env deve vir antes do nome"
    assert i_nome - i_env >= 3, ("precisa de pelo menos uma OPCAO entre --env "
                                 "e o nome do servidor (regra da doc)")
    assert args[i_nome + 1] == "--", "o nome vem logo antes do separador --"
    assert "$pyExe" in args, "registre o caminho ABSOLUTO do python"
    assert "python" not in args, "nao registre a palavra 'python' (PATH do filho)"


def test_conectar_e_idempotente_e_nao_usa_erroraction_stop():
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    assert "mcp remove lilo --scope user" in texto, "remova antes de registrar"
    codigo = "\n".join(ln for ln in texto.splitlines()
                       if not ln.lstrip().startswith("#"))
    assert "$ErrorActionPreference" not in codigo, (
        "EAP=Stop transforma stderr de comando nativo em erro terminante no "
        "PowerShell 5.1 e esconde a mensagem util")
    assert "--scope user" in codigo  # escopo user = todos os projetos


# --- stdout do servidor limpo ------------------------------------------------
def test_mcp_serve_nao_escreve_em_stdout(monkeypatch):
    """Nada pode ir para stdout: e o canal JSON-RPC."""
    registradas = []

    class ServidorFake:
        def tool(self):
            def deco(fn):
                registradas.append(fn.__name__)
                return fn
            return deco

        def run(self):
            pass

    monkeypatch.setattr(mcp_servidor, "_criar_servidor", lambda: ServidorFake())
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert mcp_servidor.main() == 0
    assert buf.getvalue() == "", "stdout sujo: %r" % buf.getvalue()[:200]
    assert set(registradas) == set(mcp_servidor.WRAPPERS)


def test_cli_nao_dispara_os_system_no_mcp_serve(monkeypatch):
    """No Windows o truque VT rodava ANTES do despacho e subia um cmd.exe
    herdando os handles do canal stdio."""
    from lilo import cli
    monkeypatch.setattr(sys, "platform", "win32")
    chamou = []
    import os as _os
    monkeypatch.setattr(_os, "system", lambda cmd: chamou.append(cmd))
    monkeypatch.setattr(mcp_servidor, "main", lambda: 0)
    assert cli.main(["mcp-serve"]) == 0
    assert chamou == [], "os.system nao pode rodar no caminho do mcp-serve"


def test_handshake_real_com_o_servidor():
    """Vivo: sobe o mcp-serve de verdade e faz o handshake (nao precisa de
    Ollama — so do pacote opcional `mcp`; pula limpo sem ele)."""
    pytest.importorskip("mcp", reason="pacote opcional 'mcp' nao instalado")
    ok, explicacao, err = diag.handshake(timeout=45)
    assert ok, "handshake falhou: %s | stderr: %s" % (explicacao, err[-500:])
