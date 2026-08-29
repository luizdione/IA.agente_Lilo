"""Testes da PONTE MCP (LILO <-> Claude Code) — v13.9 + v13.10.

Duas falhas reais na maquina do dono, ambas no comando de registro, ambas
travadas aqui:

* v13.9 — `--env` e VARIADICO: colado no nome do servidor, o CLI lia `lilo`
  como mais um par de variavel ("Invalid environment variable format").
* v13.10 — o separador `--` nem sempre sobrevive ao PowerShell/shim do npm;
  sem ele, qualquer token com `-` no comando do servidor vira opcao
  ("unknown option '-m'"). Por isso o comando registrado NAO pode ter
  hifens — e o teste abaixo garante isso.
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
def _args_add() -> list[str]:
    """Os elementos literais do array `$argsAdd` do .ps1 (o `claude mcp add`)."""
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    m = re.search(r"\$argsAdd\s*=\s*@\((.*?)\)\s*\+\s*\$cmdServidor",
                  texto, re.S)
    assert m, "array $argsAdd nao encontrado no script"
    return re.findall(r"'([^']*)'", m.group(1))


def _cmd_servidor() -> list[str]:
    """Os elementos de `$cmdServidor` (o comando do servidor propriamente)."""
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    m = re.search(r"\$cmdServidor\s*=\s*@\((.*?)\)", texto, re.S)
    assert m, "array $cmdServidor nao encontrado no script"
    return [p.strip() for p in m.group(1).split(",")]


def test_comando_do_servidor_nao_tem_hifens():
    """REGRESSAO v13.10: se o `--` for engolido pelo shell, qualquer token
    com `-` no comando vira opcao desconhecida no CLI."""
    for token in _cmd_servidor():
        assert not token.startswith("-"), (
            "token %r comeca com '-': o registro quebra quando o separador "
            "`--` nao sobrevive ao shell" % token)
    codigo = "\n".join(ln for ln in SCRIPT_PS1.read_text(encoding="utf-8").splitlines()
                       if not ln.lstrip().startswith("#"))
    assert " -m " not in codigo, "nao use `python -m ...` no comando registrado"


def test_ordem_documentada_do_claude_mcp_add():
    """REGRESSAO v13.9: `--env` e variadico — precisa de outra OPCAO entre ele
    e o nome do servidor, senao o nome e lido como variavel."""
    args = _args_add()
    assert args[:2] == ["mcp", "add"]
    i_env, i_nome = args.index("--env"), args.index("lilo")
    assert i_env < i_nome, "--env deve vir antes do nome"
    assert i_nome - i_env >= 3, ("precisa de pelo menos uma OPCAO entre --env "
                                 "e o nome do servidor (regra da doc)")
    assert args[i_nome + 1] == "--", "o nome vem logo antes do separador --"
    assert args[-1] == "--", "o comando do servidor entra depois do --"
    assert "--scope" in args and "user" in args  # escopo user = todos projetos


def test_registra_python_absoluto_e_o_lancador_dash_free():
    cmd = _cmd_servidor()
    assert "$pyExe" in cmd[0], "registre o caminho ABSOLUTO do interpretador"
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    # o 2o elemento e a variavel do lancador; conferimos de onde ela vem
    padrao = re.escape(cmd[1]) + r"\s*=\s*Join-Path[^\n]*servir_mcp\.py"
    assert re.search(padrao, texto), (
        "o comando deve apontar para o scripts/servir_mcp.py")


def test_conectar_e_idempotente_e_nao_usa_erroraction_stop():
    texto = SCRIPT_PS1.read_text(encoding="utf-8")
    assert "mcp remove lilo --scope user" in texto, "remova antes de registrar"
    codigo = "\n".join(ln for ln in texto.splitlines()
                       if not ln.lstrip().startswith("#"))
    assert "$ErrorActionPreference" not in codigo, (
        "EAP=Stop transforma stderr de comando nativo em erro terminante no "
        "PowerShell 5.1 e esconde a mensagem util")
    assert "--handshake --cmd" in codigo, (
        "o autoteste precisa validar o MESMO comando que sera registrado")


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


def test_handshake_real_pelo_servir_mcp():
    """Vivo: o lancador dash-free (servir_mcp.py) sobe o servidor e responde
    — e o MESMO comando que o .ps1 registra. Pula sem o pacote `mcp`."""
    pytest.importorskip("mcp", reason="pacote opcional 'mcp' nao instalado")
    cmd = diag.comando_padrao()
    assert cmd[1].endswith("servir_mcp.py")
    ok, explicacao, err = diag.handshake(cmd, timeout=45)
    assert ok, "handshake falhou: %s | stderr: %s" % (explicacao, err[-500:])
