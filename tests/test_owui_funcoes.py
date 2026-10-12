"""Filtros da Open WebUI (owui_funcoes/): logica pura dos inlets, sem interface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "owui_funcoes"


def carregar(nome: str):
    spec = importlib.util.spec_from_file_location("owui_" + nome, PASTA / (nome + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_profundidade_mapeia_niveis_e_nunca_toca_no_runner():
    m = carregar("profundidade")
    f = m.Filter()
    assert f.toggle is True and f.icon.startswith("data:image/svg+xml;base64,")   # botao com engrenagem
    out = f.inlet({"model": "lilo-pesquisa", "messages": [{"role": "user", "content": "oi"}],
                   "options": {"seed": 1}},
                  __user__={"valves": f.UserValves(nivel="alto")}, __model__={"owned_by": "ollama"})
    assert out["think"] is True and out["options"]["num_predict"] == 3072 and out["options"]["temperature"] == 0.6
    assert out["options"]["seed"] == 1 and "reasoning_effort" not in out and "num_ctx" not in out["options"]
    assert "max_tokens" not in out and "temperature" not in out     # Ollama: tudo em options
    out = f.inlet({"model": "lilo-orquestrador", "messages": [], "temperature": 0.7, "top_p": 0.9},
                  __user__={"valves": f.UserValves(nivel="baixo")}, __model__={"owned_by": "openai"})
    assert out["reasoning_effort"] == "low" and "think" not in out and out["max_tokens"] == 512
    assert "temperature" not in out and "top_p" not in out          # a Anthropic recusa os dois juntos
    out = f.inlet({"model": "lilo", "messages": [{"role": "system", "content": "S"}]},
                  __user__={"valves": f.UserValves(nivel="ultracode")}, __model__={"owned_by": "ollama"})
    assert out["messages"][0]["content"].startswith("S") and "Modo código" in out["messages"][0]["content"]
    out = f.inlet(out, __user__={"valves": f.UserValves(nivel="ultracode")}, __model__={"owned_by": "ollama"})
    assert out["messages"][0]["content"].count("Modo código") == 1   # nao duplica
    out = f.inlet({"model": "lilo", "messages": []}, __user__=None, __model__=None)
    assert out["options"]["num_predict"] == 1536 and out["think"] is False   # padrao = medio


def test_modo_restringe_tools_de_verdade():
    m = carregar("modo")
    f = m.Filter()
    assert f.toggle is True and f.icon.startswith("data:image/svg+xml;base64,")
    ids = ["server:mcp:analise", "server:mcp:exec", "server:mcp:conhecimento",
           "server:desktop|tool_write_file_post", "server:mcp:literatura"]
    meta = {"tool_ids": list(ids)}
    out = f.inlet({"messages": [], "tool_ids": list(ids)}, __user__={"valves": f.UserValves(modo="manual")}, __metadata__=meta)
    assert meta["tool_ids"] == out["tool_ids"]
    assert "server:mcp:exec" not in meta["tool_ids"]
    assert any(t.startswith("server:mcp:analise|estat_descrever") for t in meta["tool_ids"])
    desk = [t for t in meta["tool_ids"] if t.startswith("server:desktop")][0]
    assert "tool_read_file_post" in desk and "tool_write_file_post" not in desk
    assert "server:mcp:conhecimento" in meta["tool_ids"] and "server:mcp:literatura" in meta["tool_ids"]
    assert "Modo manual" in out["messages"][0]["content"]

    meta = {"tool_ids": list(ids)}
    f.inlet({"messages": []}, __user__={"valves": f.UserValves(modo="aceitar_edicoes")}, __metadata__=meta)
    desk = [t for t in meta["tool_ids"] if t.startswith("server:desktop")][0]
    assert "tool_edit_block_post" in desk and "tool_start_process_post" not in desk
    assert "server:mcp:analise" in meta["tool_ids"] and "server:mcp:exec" not in meta["tool_ids"]

    meta = {"tool_ids": list(ids)}
    out = f.inlet({"messages": []}, __user__={"valves": f.UserValves(modo="plano")}, __metadata__=meta)
    assert meta["tool_ids"] == [] and "Modo plano" in out["messages"][0]["content"]

    for modo in ("automatico", "ignorar_permissoes"):
        meta = {"tool_ids": list(ids)}
        f.inlet({"messages": []}, __user__={"valves": f.UserValves(modo=modo)}, __metadata__=meta)
        assert meta["tool_ids"] == ids
    assert m.restringir(None, "manual") == []


def test_botoes_da_caixa():
    pensar, plano, pasta = carregar("pensar"), carregar("plano"), carregar("pasta")
    for mod in (pensar, plano, pasta):
        f = mod.Filter()
        assert f.toggle is True and f.icon.startswith("data:image/svg+xml;base64,")
    out = pensar.Filter().inlet({"messages": []}, __model__={"owned_by": "ollama"})
    assert out["think"] is True and out["options"]["num_predict"] == 3072
    out = pensar.Filter().inlet({"messages": [], "top_p": 0.9}, __model__={"owned_by": "openai"})
    assert out["reasoning_effort"] == "high" and "top_p" not in out
    meta = {"tool_ids": ["server:mcp:exec"]}
    out = plano.Filter().inlet({"messages": [{"role": "system", "content": "S"}], "tool_ids": ["x"]}, __metadata__=meta)
    assert meta["tool_ids"] == [] and out["tool_ids"] == [] and "Modo plano" in out["messages"][0]["content"]
    f = pasta.Filter()
    out = f.inlet({"messages": []}, __user__={"valves": f.UserValves(caminho=r"C:\GitHub\LILO")})
    assert r"C:\GitHub\LILO" in out["messages"][0]["content"]
    out = f.inlet({"messages": []}, __user__={"valves": f.UserValves(caminho="")})
    assert "pasta_escolher" in out["messages"][0]["content"]
