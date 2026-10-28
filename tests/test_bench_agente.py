"""bench_agente.py sem GPU: pontuacao de cada tarefa, laco com Ollama falso, guardas e JSONL."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("bench_agente", ROOT / "scripts" / "bench_agente.py")
ba = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ba)


def test_preparar_e_pontuar_medias_csv(tmp_path):
    gab = ba.preparar("medias_csv", tmp_path)
    assert (tmp_path / "dados.csv").exists() and set(gab["medias"]) == {"A", "B", "C"}
    pontos, faltas = ba.pontuar("medias_csv", tmp_path, gab, "", [])
    assert pontos == 0 and len(faltas) == 4
    (tmp_path / "medias.py").write_text(
        "import csv, collections\n"
        "d = collections.defaultdict(list)\n"
        "for r in csv.DictReader(open('dados.csv', encoding='utf-8')):\n"
        "    d[r['grupo']].append(float(r['valor']))\n"
        "for g in sorted(d):\n"
        "    print(g, round(sum(d[g]) / len(d[g]), 2))\n", encoding="utf-8")
    resposta = "Médias: " + ", ".join("%s = %.2f" % (g, m) for g, m in gab["medias"].items())
    trans = [{"tool": "executar_python", "args": {"codigo": "exec(open('medias.py').read())"}, "saida": "A 10"}]
    pontos, faltas = ba.pontuar("medias_csv", tmp_path, gab, resposta, trans)
    assert pontos == 4, faltas


def test_pontuar_corrigir_bug(tmp_path):
    gab = ba.preparar("corrigir_bug", tmp_path)
    pontos, faltas = ba.pontuar("corrigir_bug", tmp_path, gab, "", [])
    assert "pytest passa" in faltas and "teste intacto" not in faltas
    (tmp_path / "mod.py").write_text("def mediana(xs):\n    s = sorted(xs)\n    n = len(s)\n"
                                     "    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2\n",
                                     encoding="utf-8")
    trans = [{"tool": "executar_powershell", "args": {"comando": "python -m pytest -q"}, "saida": "3 passed"}]
    pontos, faltas = ba.pontuar("corrigir_bug", tmp_path, gab, "pronto", trans)
    assert pontos == 4, faltas
    (tmp_path / "test_mod.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    pontos, faltas = ba.pontuar("corrigir_bug", tmp_path, gab, "pronto", trans)
    assert "teste intacto" in faltas


def test_pontuar_resumo_md(tmp_path):
    gab = ba.preparar("resumo_md", tmp_path)
    (tmp_path / "resumo.md").write_text("# T\n## Objetivo\nAvaliar X em 48 amostras e 3 grupos.\n"
                                        "## Resultados\nQueda de 17% (p = 0,012).\n## Conclusão\nReduz.\n",
                                        encoding="utf-8")
    pontos, faltas = ba.pontuar("resumo_md", tmp_path, gab, "", [])
    assert pontos == 4, faltas
    (tmp_path / "resumo.md").write_text("## A\n99 amostras\n## B\n## C\n## D\n", encoding="utf-8")
    pontos, faltas = ba.pontuar("resumo_md", tmp_path, gab, "", [])
    assert "exatamente 3 secoes ##" in faltas and "nenhum numero fora da fonte" in faltas


def test_pontuar_teste_t(tmp_path):
    gab = ba.preparar("teste_t", tmp_path)
    resp = "t = %.2f, p = %.4f: diferença significativa entre TRAT e CTRL." % (gab["t"], gab["p"])
    trans = [{"tool": "estat_teste_t", "args": {"csv": str(tmp_path / "ensaio.csv"), "coluna": "valor", "grupo": "grupo"}}]
    pontos, faltas = ba.pontuar("teste_t", tmp_path, gab, resp, trans)
    esperado = 4 if gab["p"] < 0.05 else 3
    assert pontos == esperado, (faltas, gab["p"])
    pontos, faltas = ba.pontuar("teste_t", tmp_path, gab, "não sei", [])
    assert pontos == 0


def test_laco_com_ollama_falso_e_tool_executada(tmp_path, monkeypatch):
    monkeypatch.setattr(ba.comum, "gpu_reservada", lambda: None)
    alvo = tmp_path / "saida.txt"
    respostas = [
        {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {
            "name": "arquivo_escrever", "arguments": {"caminho": str(alvo), "conteudo": "ola"}}}]},
         "prompt_eval_count": 1000, "prompt_eval_duration": int(1e9), "eval_count": 20, "eval_duration": int(1e9),
         "load_duration": 0, "done_reason": "stop"},
        {"message": {"role": "assistant", "content": "Gravei o arquivo."},
         "prompt_eval_count": 1100, "prompt_eval_duration": int(0.1e9), "eval_count": 10, "eval_duration": int(0.5e9),
         "load_duration": 0, "done_reason": "stop"},
    ]
    pedidos: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        pedidos.append(json.loads(req.content))
        return httpx.Response(200, json=respostas[len(pedidos) - 1])

    executadas: list[tuple] = []

    async def fake_exec(grupo, nome, args):
        executadas.append((grupo, nome, args))
        Path(args["caminho"]).write_text(args["conteudo"], encoding="utf-8")
        return "[ok] gravado", False

    tools = [{"type": "function", "function": {"name": "arquivo_escrever", "description": "",
                                                "parameters": {"type": "object", "properties": {
                                                    "caminho": {"type": "string"}, "conteudo": {"type": "string"}},
                                                               "required": ["caminho", "conteudo"]}}}]
    run = ba.Run("falso", "medias_csv", 1, "t")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            await ba.rodar_run(cli, run, "grave ola", tools, {"arquivo_escrever": "codigo"}, False, 5,
                               prefill_tps=1000.0, salvar=tmp_path / "trans", executar=fake_exec)
    asyncio.run(go())
    assert executadas == [("codigo", "arquivo_escrever", {"caminho": str(alvo), "conteudo": "ola"})]
    assert alvo.read_text(encoding="utf-8") == "ola" and run.resposta == "Gravei o arquivo." and run.motivo == "respondeu"
    assert len(run.passos) == 2 and run.passos[0]["reuso"] == 0.0 and run.passos[1]["reuso"] > 0.9
    assert pedidos[1]["messages"][-1] == {"role": "tool", "tool_name": "arquivo_escrever", "content": "[ok] gravado"}
    assert pedidos[0]["think"] is False and pedidos[0]["tools"] == tools
    assert run.falhas["args_invalidos"] == 0 and list((tmp_path / "trans").glob("*.json"))


def test_laco_detecta_loop_e_vazamento(tmp_path, monkeypatch):
    monkeypatch.setattr(ba.comum, "gpu_reservada", lambda: None)
    chamada = {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {
        "name": "arquivo_listar", "arguments": {"caminho": "x"}}}]}, "prompt_eval_count": 10,
        "prompt_eval_duration": 1, "eval_count": 1, "eval_duration": 1, "load_duration": 0}

    def handler(req):
        return httpx.Response(200, json=chamada)

    async def fake_exec(grupo, nome, args):
        return "[ok] nada", False

    run = ba.Run("falso", "x", 1, "t")
    tools = [{"type": "function", "function": {"name": "arquivo_listar", "description": "", "parameters": {"type": "object"}}}]

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            await ba.rodar_run(cli, run, "x", tools, {"arquivo_listar": "codigo"}, None, 10, 0.0, None, executar=fake_exec)
    asyncio.run(go())
    assert run.motivo.startswith("loop") and run.falhas["loop"] == 1 and len(run.passos) == 3
    assert ba._vazou_tool_call('{"name": "arquivo_ler", "arguments": {}}') and ba._vazou_tool_call("<tool_call>x")
    assert not ba._vazou_tool_call("A média é 10.")


def test_interruptor_off_sai_com_3(monkeypatch, capsys):
    monkeypatch.setattr(ba.comum, "gpu_reservada", lambda: "MD do dono")
    a = type("A", (), {"ignorar_gpu_ocupada": False, "ferramentas": "ambas", "modelos": ["lilo"],
                       "tarefas": ["medias_csv"], "repeticoes": 1, "max_passos": 3, "salvar_transcricao": False,
                       "sem_portao": False, "descarregar": False})()
    assert asyncio.run(ba.principal(a)) == 3
    assert "DESLIGADO" in capsys.readouterr().out


def test_resumo_e_portao():
    def run(tarefa, passou, s=30.0):
        return {"tarefa": tarefa, "passou": passou, "tool_calls": 3, "tempo_total_s": s, "resposta": "ok",
                "falhas": {"args_invalidos": 0, "vazou": 0, "http500": 0, "loop": 0},
                "passos": [{"s": 5.0, "prompt_tok": 3000, "eval_tok": 50, "eval_s": 2.0, "carga_s": 0.0,
                            "thinking_chars": 0, "reuso": None},
                           {"s": 4.0, "prompt_tok": 3500, "eval_tok": 50, "eval_s": 2.0, "carga_s": 0.0,
                            "thinking_chars": 0, "reuso": 0.95}]}
    runs = [run("medias_csv", True), run("corrigir_bug", True), run("resumo_md", True), run("teste_t", True)]
    r = ba.resumo_modelo("m", runs, 32768)
    assert r["passou_portao"] and r["aprovadas"] == 4 and r["reuso_medio"] == 0.95 and r["tps"] == 25.0
    runs[1]["passou"] = False
    runs.append(run("corrigir_bug", False, 400.0))
    r2 = ba.resumo_modelo("m", runs, 32768)
    assert not r2["passou_portao"] and any("corrigir_bug" in f for f in r2["portao_falhas"])


def test_embed_recente(tmp_path):
    log = tmp_path / "server.log"
    import time
    agora = time.strftime("%Y/%m/%d - %H:%M:%S")
    log.write_text('[GIN] 2020/01/01 - 00:00:00 | 200 | 1ms | ::1 | POST "/api/embed"\n', encoding="utf-8")
    assert not ba.embed_recente(log=log)
    log.write_text('[GIN] %s | 200 | 1ms | ::1 | POST "/api/embed"\n' % agora, encoding="utf-8")
    assert ba.embed_recente(log=log)
    assert not ba.embed_recente(log=tmp_path / "nao_existe.log")
