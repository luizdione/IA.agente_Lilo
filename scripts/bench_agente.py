"""Bench AGENTICO do LILO: laco de tools de verdade contra o Ollama e a ponte lilo-host.

    python scripts\\bench_agente.py --modelos cand-coder,cand-2507,cand-oss --repeticoes 3
    python scripts\\bench_agente.py --modelos lilo --tarefas medias_csv --max-passos 8 --sem-portao

Para cada modelo x tarefa x repeticao: POST /api/chat (stream False) com os schemas REAIS das
tools da ponte (conhecimento + analise + exec + codigo); cada tool_call e executada na ponte
(cliente MCP streamable HTTP) e devolvida como role=tool; repete ate o modelo responder sem
tool_calls, bater o teto de passos ou entrar em laco (3x a mesma chamada). Pontua com
verificacoes EXTERNAS (arquivo existe, reexecucao bate, pytest passa...). O `bench.py` mede a
latencia do chat; este mede se o modelo CONCLUI tarefas com ferramentas, e a que custo.

Guardas (falha fechada): interruptor de GPU (comum.gpu_reservada), GPU ocupada por outro job,
`/api/embed` recente no server.log do Ollama (lumen reindexando). Codigos de saida: 0 passou,
1 portao falhou, 2 infraestrutura (Ollama, ponte, token), 3 GPU indisponivel.
Saida: %LOCALAPPDATA%\\LILO\\bench\\agente.jsonl (1 linha por run + 1 resumo por modelo).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402

from lilo_host import comum  # noqa: E402
from lilo_host.comum import OLLAMA, token_exec  # noqa: E402

PONTE = os.environ.get("LILO_PONTE", "http://127.0.0.1:8790")
GRUPOS = ("conhecimento", "analise", "exec", "codigo")
COM_TOKEN = {"exec", "codigo"}
SAIDA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LILO" / "bench"
SERVER_LOG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Ollama" / "server.log"
# Tools fora do bench: abrem janela, carregam outro modelo na GPU, agem fora da pasta de teste
# ou carregam o embedder (~30 s).
EXCLUIDAS = {"pasta_escolher", "resumir_arquivo", "executar_git", "skill_rodar", "executar_wsl",
             "biblioteca_buscar", "biblioteca_status"}
TAREFAS = ("medias_csv", "corrigir_bug", "resumo_md", "teste_t")
# Portao G-B (plano de 28/10): calibrar depois das primeiras medicoes.
PORTAO = {"runs_min_frac": 0.75, "tarefa_zero": False, "bug_min": 2, "falha_json_max": 0.05,
          "mediana_tarefa_s": 120.0, "mediana_bug_s": 240.0, "mediana_passo_s": 15.0,
          "reuso_min": 0.80, "prompt_frac_max": 0.80, "thinking_frac_max": 0.30, "tps_min": 12.0}

SYSTEM_BENCH = ("Você é o LILO, assistente local de pesquisa. Responda em português do Brasil. Você TEM "
                "ferramentas e deve usá-las para cumprir a tarefa de ponta a ponta: leia com arquivo_ler, "
                "crie com arquivo_escrever, altere com arquivo_editar, rode com executar_python ou "
                "executar_powershell, e verifique o resultado antes de responder. Use caminhos absolutos. "
                "Termine com uma resposta curta com os números pedidos.")


# ----------------------------------------------------------------- guardas
def gpu_ocupada(limite_uso: int = 30) -> str | None:
    """Uso da GPU acima do limite ou VRAM quase cheia = outro job rodando (MD, Boltz, render)."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        uso, usada, total = [int(x.strip()) for x in r.stdout.strip().split(",")]
    except Exception:  # noqa: BLE001 - sem nvidia-smi nao barra (maquina de CI)
        return None
    if uso > limite_uso:
        return "GPU em uso por outro job (%d%%)" % uso
    if total - usada < 1500:
        return "VRAM quase cheia (%d de %d MiB)" % (usada, total)
    return None


def embed_recente(segundos: int = 120, log: Path = SERVER_LOG) -> bool:
    """Chamadas /api/embed nos ultimos `segundos` = plugin lumen indexando na GPU (contamina)."""
    try:
        with log.open("rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 200_000))
            cauda = fh.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return False
    agora = time.time()
    for linha in reversed(cauda[-400:]):
        if "/api/embed" not in linha:
            continue
        m = re.search(r"\[GIN\] (\d{4})/(\d{2})/(\d{2}) - (\d{2}):(\d{2}):(\d{2})", linha)
        if not m:
            continue
        t = time.mktime(tuple(int(x) for x in m.groups()) + (0, 0, -1))
        return agora - t < segundos
    return False


# -------------------------------------------------------------- ponte (MCP)
async def _sessao(grupo: str):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers = {"Authorization": "Bearer " + token_exec(gerar=False)} if grupo in COM_TOKEN else None
    return streamablehttp_client(f"{PONTE}/{grupo}/mcp", headers=headers), ClientSession


async def schemas() -> tuple[list[dict], dict[str, str]]:
    """Schemas (formato tools do Ollama) e mapa tool -> grupo, em ordem estavel."""
    ferramentas, grupo_de = [], {}
    for g in GRUPOS:
        ctx, Sessao = await _sessao(g)
        async with ctx as (r, w, _):
            async with Sessao(r, w) as s:
                await s.initialize()
                for t in sorted((await s.list_tools()).tools, key=lambda x: x.name):
                    if t.name in EXCLUIDAS:
                        continue
                    grupo_de[t.name] = g
                    ferramentas.append({"type": "function", "function": {
                        "name": t.name, "description": t.description or "", "parameters": t.inputSchema}})
    return ferramentas, grupo_de


async def executar_tool(grupo: str, nome: str, args: dict) -> tuple[str, bool]:
    ctx, Sessao = await _sessao(grupo)
    async with ctx as (r, w, _):
        async with Sessao(r, w) as s:
            await s.initialize()
            res = await s.call_tool(nome, args)
            texto = "".join(getattr(c, "text", "") for c in res.content)
            return texto, bool(res.isError) or texto.startswith("[ERRO]")


# ----------------------------------------------------------------- tarefas
def _csv(p: Path, linhas: list[tuple[str, float]]) -> None:
    p.write_text("grupo,valor\n" + "\n".join("%s,%.3f" % x for x in linhas) + "\n", encoding="utf-8")


def preparar(tarefa: str, pasta: Path, semente: int = 7) -> dict:
    """Cria os insumos da tarefa na pasta e devolve o pedido + o gabarito."""
    rnd = random.Random(semente)
    pasta.mkdir(parents=True, exist_ok=True)
    if tarefa == "medias_csv":
        linhas = [(g, rnd.gauss(m, 1.0)) for g, m in (("A", 10), ("B", 20), ("C", 30)) for _ in range(8)]
        _csv(pasta / "dados.csv", linhas)
        medias = {g: statistics.mean(v for gg, v in linhas if gg == g) for g in "ABC"}
        return {"pedido": f"Na pasta {pasta} existe dados.csv (colunas grupo,valor). Crie {pasta / 'medias.py'} "
                          "que lê o CSV e imprime a média de valor por grupo com 2 casas decimais, rode o "
                          "script e me diga as três médias.", "medias": medias}
    if tarefa == "corrigir_bug":
        (pasta / "mod.py").write_text("def mediana(xs):\n    s = sorted(xs)\n    n = len(s)\n"
                                      "    return s[n // 2]\n", encoding="utf-8")
        teste = ("from mod import mediana\n\n\ndef test_impar():\n    assert mediana([3, 1, 2]) == 2\n\n\n"
                 "def test_par():\n    assert mediana([1, 2, 3, 4]) == 2.5\n\n\n"
                 "def test_um():\n    assert mediana([9]) == 9\n")
        (pasta / "test_mod.py").write_text(teste, encoding="utf-8")
        # hash dos BYTES gravados (no Windows o write_text troca \n por \r\n)
        return {"pedido": f"Em {pasta}, o teste test_mod.py falha. Corrija mod.py (não altere o teste) e prove "
                          "rodando pytest nessa pasta.",
                "hash_teste": hashlib.sha256((pasta / "test_mod.py").read_bytes()).hexdigest(),
                "mod_original": (pasta / "mod.py").read_text(encoding="utf-8")}
    if tarefa == "resumo_md":
        fatos = ["48", "3", "0,012", "17"]
        texto = ("Efeito do composto X na viabilidade de células HepG2\n\nObjetivo: avaliar se o composto X "
                 "reduz a viabilidade celular. Métodos: 48 amostras divididas em 3 grupos (controle, 10 uM e "
                 "50 uM), ensaio de MTT em 72 h. Resultados: na dose de 50 uM a viabilidade caiu 17% em "
                 "relação ao controle (p = 0,012, ANOVA com Tukey); a dose de 10 uM não diferiu do controle. "
                 "Conclusão: o composto X reduz a viabilidade de HepG2 apenas na dose maior.\n")
        fonte = pasta / "artigo.txt"
        fonte.write_text(texto, encoding="utf-8")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open()
            pg = doc.new_page()
            y = 72
            for linha in re.findall(r".{1,90}(?:\s|$)", texto):
                pg.insert_text((54, y), linha.strip())
                y += 14
            doc.save(str(pasta / "artigo.pdf"))
            doc.close()
            fonte = pasta / "artigo.pdf"
        except Exception:  # noqa: BLE001 - sem PyMuPDF fica o .txt
            pass
        return {"pedido": f"Leia {fonte} e grave {pasta / 'resumo.md'} com exatamente três seções de nível 2 "
                          "(## Objetivo, ## Resultados, ## Conclusão), citando os números do texto. Depois "
                          "confirme o que gravou.", "fatos": fatos, "fonte": texto}
    if tarefa == "teste_t":
        linhas = [("CTRL", rnd.gauss(10.0, 1.5)) for _ in range(12)] + [("TRAT", rnd.gauss(12.0, 1.5)) for _ in range(12)]
        _csv(pasta / "ensaio.csv", linhas)
        from scipy import stats
        a = [v for g, v in linhas if g == "CTRL"]
        b = [v for g, v in linhas if g == "TRAT"]
        t, p = stats.ttest_ind(b, a, equal_var=False)
        return {"pedido": f"Compare TRAT com CTRL em {pasta / 'ensaio.csv'} (coluna valor, grupos na coluna "
                          "grupo) com um teste t de Welch usando a ferramenta estat_teste_t e escreva um laudo "
                          "de até 5 linhas com t, p e a conclusão.", "t": float(t), "p": float(p)}
    raise ValueError("tarefa desconhecida: " + tarefa)


def _numeros(texto: str) -> list[float]:
    out = []
    for m in re.findall(r"-?\d+(?:[.,]\d+)?", texto):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            pass
    return out


def _chamou(trans: list[dict], nome: str, contendo: str = "") -> bool:
    for ev in trans:
        if ev.get("tool") == nome and contendo.lower() in json.dumps(ev.get("args", {}), ensure_ascii=False).lower():
            return True
    return False


def pontuar(tarefa: str, pasta: Path, gab: dict, resposta: str, trans: list[dict]) -> tuple[int, list[str]]:
    """Pontos objetivos (0-4) e o que faltou."""
    faltas: list[str] = []
    if tarefa == "medias_csv":
        script = pasta / "medias.py"
        ok1 = script.exists()
        if ok1:
            try:
                compile(script.read_text(encoding="utf-8"), str(script), "exec")
            except SyntaxError:
                ok1 = False
        ok2 = False
        if ok1:
            r = subprocess.run([sys.executable, str(script)], cwd=str(pasta), capture_output=True, text=True, timeout=60)
            nums = _numeros(r.stdout)
            ok2 = all(any(abs(n - m) <= 0.01 for n in nums) for m in gab["medias"].values())
        ok3 = any(ev.get("tool") in ("executar_python", "executar_powershell") and "medias" in json.dumps(ev.get("args", {}))
                  for ev in trans)
        nums = _numeros(resposta)
        ok4 = all(any(abs(n - m) <= 0.01 for n in nums) for m in gab["medias"].values())
        for ok, nome in ((ok1, "script existe e compila"), (ok2, "reexecucao da as medias"), (ok3, "rodou o script"),
                         (ok4, "resposta traz as medias")):
            if not ok:
                faltas.append(nome)
    elif tarefa == "corrigir_bug":
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_mod.py"],
                           cwd=str(pasta), capture_output=True, text=True, timeout=120)
        ok1 = r.returncode == 0
        ok2 = hashlib.sha256((pasta / "test_mod.py").read_bytes()).hexdigest() == gab["hash_teste"]
        atual = (pasta / "mod.py").read_text(encoding="utf-8") if (pasta / "mod.py").exists() else ""
        import difflib
        mudadas = [x for x in difflib.unified_diff(gab["mod_original"].splitlines(), atual.splitlines(), n=0)
                   if x[:1] in "+-" and not x.startswith(("+++", "---"))]
        ok3 = 0 < len(mudadas) <= 6
        ok4 = any(ev.get("tool") in ("executar_python", "executar_powershell") and "passed" in ev.get("saida", "")
                  for ev in trans)
        for ok, nome in ((ok1, "pytest passa"), (ok2, "teste intacto"), (ok3, "diff minimo em mod.py"),
                         (ok4, "mostrou pytest verde")):
            if not ok:
                faltas.append(nome)
    elif tarefa == "resumo_md":
        arq = pasta / "resumo.md"
        texto = arq.read_text(encoding="utf-8") if arq.exists() else ""
        ok1 = bool(texto.strip())
        ok2 = len(re.findall(r"^## ", texto, re.M)) == 3
        ok3 = sum(1 for f in gab["fatos"] if f in texto.replace(".", ",")) >= 3
        fonte = set(_numeros(gab["fonte"])) | {1.0, 2.0, 3.0}
        ok4 = ok1 and all(n in fonte for n in _numeros(re.sub(r"^#.*$", "", texto, flags=re.M)))
        for ok, nome in ((ok1, "resumo.md existe"), (ok2, "exatamente 3 secoes ##"), (ok3, ">=3 fatos"),
                         (ok4, "nenhum numero fora da fonte")):
            if not ok:
                faltas.append(nome)
    elif tarefa == "teste_t":
        ok1 = _chamou(trans, "estat_teste_t", "ensaio.csv")
        nums = _numeros(resposta)
        p, t = gab["p"], gab["t"]
        ok2 = any(abs(n - p) <= max(0.002, 0.05 * p) for n in nums)
        ok3 = any(abs(n - t) <= 0.02 for n in nums)
        sig = p < 0.05
        diz_sig = bool(re.search(r"signific", resposta, re.I))
        diz_nao = bool(re.search(r"n[aã]o\s+(?:\w+\s+){0,3}signific", resposta, re.I))
        linhas = [x for x in resposta.splitlines() if x.strip()]
        ok4 = ((diz_sig and not diz_nao) if sig else diz_nao) and len(linhas) <= 8
        for ok, nome in ((ok1, "chamou estat_teste_t"), (ok2, "p correto"), (ok3, "t correto"),
                         (ok4, "conclusao coerente e curta")):
            if not ok:
                faltas.append(nome)
    else:
        faltas.append("tarefa desconhecida")
    return 4 - len(faltas), faltas


# -------------------------------------------------------------- laco agentico
def _think(modelo: str, capacidades: list[str]):
    if "oss" in modelo:
        return "low"
    if "thinking" in capacidades:
        return False
    return None   # modelo sem modo pensante: nao mandar o campo


def _vazou_tool_call(conteudo: str) -> bool:
    c = (conteudo or "").strip()
    return "<tool_call>" in c or (c.startswith("{") and '"name"' in c and '"arguments"' in c)


def _valida(args: dict, schema: dict) -> bool:
    try:
        import jsonschema
    except ImportError:
        return True
    try:
        jsonschema.validate(args, schema)
        return True
    except Exception:  # noqa: BLE001
        return False


class Run:
    def __init__(self, modelo: str, tarefa: str, rep: int, run_id: str):
        self.modelo, self.tarefa, self.rep, self.run_id = modelo, tarefa, rep, run_id
        self.passos: list[dict] = []
        self.trans: list[dict] = []
        self.falhas = {"vazou": 0, "args_invalidos": 0, "tool_inexistente": 0, "http500": 0, "tool_erro": 0, "loop": 0}
        self.tempo_tools = 0.0
        self.resposta = ""
        self.motivo = ""


async def rodar_run(cli: httpx.AsyncClient, run: Run, pedido: str, tools: list[dict], grupo_de: dict,
                    think, max_passos: int, prefill_tps: float, salvar: Path | None,
                    executar=executar_tool) -> None:
    schema_de = {t["function"]["name"]: t["function"]["parameters"] for t in tools}
    msgs: list[dict] = [{"role": "system", "content": SYSTEM_BENCH}, {"role": "user", "content": pedido}]
    assinaturas: list[str] = []
    for passo in range(1, max_passos + 1):
        if comum.gpu_reservada():
            run.motivo = "interruptor OFF durante a run"
            break
        corpo: dict = {"model": run.modelo, "stream": False, "messages": msgs, "tools": tools}
        if think is not None:
            corpo["think"] = think
        t0 = time.perf_counter()
        try:
            r = await cli.post(f"{OLLAMA}/api/chat", json=corpo)
        except httpx.HTTPError as e:
            run.motivo = "ollama: %s" % e
            break
        dt = time.perf_counter() - t0
        if r.status_code >= 500:
            run.falhas["http500"] += 1
            run.motivo = "HTTP %d: %s" % (r.status_code, r.text[:120])
            break
        d = r.json()
        msg = d.get("message") or {}
        pe, ped = d.get("prompt_eval_count", 0), d.get("prompt_eval_duration", 0) / 1e9
        reuso = (1 - min(1.0, ped * prefill_tps / pe)) if (pe and prefill_tps) else None
        run.passos.append({"passo": passo, "s": round(dt, 2), "prompt_tok": pe, "prompt_eval_s": round(ped, 3),
                           "eval_tok": d.get("eval_count", 0), "eval_s": round(d.get("eval_duration", 0) / 1e9, 3),
                           "carga_s": round(d.get("load_duration", 0) / 1e9, 2), "done": d.get("done_reason"),
                           "thinking_chars": len(msg.get("thinking") or ""), "reuso": reuso,
                           "tool_calls": len(msg.get("tool_calls") or [])})
        msgs.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            run.resposta = msg.get("content") or ""
            if _vazou_tool_call(run.resposta):
                run.falhas["vazou"] += 1
                run.motivo = "tool_call vazou como texto"
            else:
                run.motivo = "respondeu"
            break
        for c in calls:
            fn = c.get("function") or {}
            nome, args = fn.get("name", ""), fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    run.falhas["args_invalidos"] += 1
                    args = {}
            ass = nome + json.dumps(args, sort_keys=True, ensure_ascii=False)
            assinaturas.append(ass)
            if assinaturas.count(ass) >= 3:
                run.falhas["loop"] += 1
                run.motivo = "loop: 3x " + nome
                break
            if nome not in grupo_de:
                run.falhas["tool_inexistente"] += 1
                saida, erro_ = "[ERRO] ferramenta inexistente: %s" % nome, True
            else:
                if not _valida(args, schema_de.get(nome, {})):
                    run.falhas["args_invalidos"] += 1
                t1 = time.perf_counter()
                try:
                    saida, erro_ = await executar(grupo_de[nome], nome, args)
                except Exception as e:  # noqa: BLE001
                    saida, erro_ = "[ERRO] ponte: %s" % e, True
                run.tempo_tools += time.perf_counter() - t1
            if erro_:
                run.falhas["tool_erro"] += 1
            run.trans.append({"passo": passo, "tool": nome, "args": args, "saida": saida[:4000], "erro": erro_})
            msgs.append({"role": "tool", "tool_name": nome, "content": saida})
        if run.motivo.startswith("loop"):
            break
    else:
        run.motivo = "teto de %d passos" % max_passos
    if salvar:
        salvar.mkdir(parents=True, exist_ok=True)
        (salvar / f"{run.run_id}_{run.modelo}_{run.tarefa}_{run.rep}.json").write_text(
            json.dumps({"mensagens": msgs, "transcricao": run.trans}, ensure_ascii=False, indent=1), encoding="utf-8")


async def calibrar_prefill(cli: httpx.AsyncClient, modelo: str, think) -> float:
    """tok/s de prefill com ~1,5k tokens ineditos (base da estimativa de reuso de cache)."""
    rnd = random.Random(time.time())
    palavras = " ".join("%s%d" % (rnd.choice(["gato", "rio", "pedra", "azul", "norte", "folha"]), rnd.randint(1, 9999))
                        for _ in range(900))
    corpo: dict = {"model": modelo, "stream": False, "options": {"num_predict": 1},
                   "messages": [{"role": "user", "content": "Ignore e responda ok: " + palavras}]}
    if think is not None:
        corpo["think"] = think
    r = await cli.post(f"{OLLAMA}/api/chat", json=corpo)
    r.raise_for_status()
    d = r.json()
    ped = d.get("prompt_eval_duration", 0) / 1e9
    return (d.get("prompt_eval_count", 0) / ped) if ped > 0 else 0.0


async def info_modelo(cli: httpx.AsyncClient, modelo: str) -> dict:
    r = await cli.post(f"{OLLAMA}/api/show", json={"model": modelo})
    r.raise_for_status()
    d = r.json()
    return {"capacidades": d.get("capabilities") or [], "digest": (d.get("details") or {}).get("digest", ""),
            "num_ctx": (d.get("model_info") or {}).get("general.context_length")}


async def ps_modelo(cli: httpx.AsyncClient, modelo: str) -> dict:
    r = await cli.get(f"{OLLAMA}/api/ps")
    for m in (r.json().get("models") or []):
        if m.get("name", "").split(":")[0] == modelo.split(":")[0]:
            return {"context_length": m.get("context_length"), "size": m.get("size"), "size_vram": m.get("size_vram")}
    return {}


# ----------------------------------------------------------------- resumo
def resumo_modelo(modelo: str, runs: list[dict], num_ctx: int | None) -> dict:
    por_tarefa: dict[str, list[dict]] = {}
    for r in runs:
        por_tarefa.setdefault(r["tarefa"], []).append(r)
    aprov = sum(1 for r in runs if r["passou"])
    passos = [p for r in runs for p in r["passos"]]
    tc = sum(r["tool_calls"] for r in runs) or 1
    f_json = sum(r["falhas"]["args_invalidos"] + r["falhas"]["vazou"] + r["falhas"]["http500"] for r in runs) / tc
    med = {t: statistics.median(x["tempo_total_s"] for x in rs) for t, rs in por_tarefa.items()}
    reusos = [p["reuso"] for r in runs for p in r["passos"][1:] if p.get("reuso") is not None]
    ev_tok = sum(p["eval_tok"] for p in passos)
    ev_s = sum(p["eval_s"] for p in passos)
    think = sum(p["thinking_chars"] for p in passos)
    out = {"tipo": "resumo", "modelo": modelo, "runs": len(runs), "aprovadas": aprov,
           "por_tarefa": {t: "%d/%d" % (sum(1 for x in rs if x["passou"]), len(rs)) for t, rs in por_tarefa.items()},
           "falha_json_frac": round(f_json, 3), "mediana_s": {t: round(v, 1) for t, v in med.items()},
           "mediana_passo_s": round(statistics.median(p["s"] for p in passos), 2) if passos else None,
           "reuso_medio": round(statistics.mean(reusos), 2) if reusos else None,
           "recargas_apos_1": sum(1 for r in runs for p in r["passos"][1:] if p["carga_s"] > 1.0),
           "prompt_max": max((p["prompt_tok"] for p in passos), default=0),
           "tps": round(ev_tok / ev_s, 1) if ev_s else None,
           "thinking_frac": round(think / max(1, sum(len(r["resposta"]) for r in runs) + think), 2),
           "loops": sum(r["falhas"]["loop"] for r in runs)}
    falhas = []
    if runs and aprov < PORTAO["runs_min_frac"] * len(runs):
        falhas.append("aprovadas %d/%d" % (aprov, len(runs)))
    for t, rs in por_tarefa.items():
        if not any(x["passou"] for x in rs):
            falhas.append("tarefa %s 0/%d" % (t, len(rs)))
    bug = por_tarefa.get("corrigir_bug", [])
    if bug and sum(1 for x in bug if x["passou"]) < min(PORTAO["bug_min"], len(bug)):
        falhas.append("corrigir_bug abaixo do minimo")
    if f_json > PORTAO["falha_json_max"]:
        falhas.append("falhas de JSON/args %.0f%%" % (100 * f_json))
    for t, v in med.items():
        lim = PORTAO["mediana_bug_s"] if t == "corrigir_bug" else PORTAO["mediana_tarefa_s"]
        if v > lim:
            falhas.append("mediana %s %.0f s > %.0f" % (t, v, lim))
    if out["mediana_passo_s"] and out["mediana_passo_s"] > PORTAO["mediana_passo_s"]:
        falhas.append("mediana por passo %.1f s" % out["mediana_passo_s"])
    if out["reuso_medio"] is not None and out["reuso_medio"] < PORTAO["reuso_min"]:
        falhas.append("reuso de cache %.0f%%" % (100 * out["reuso_medio"]))
    if out["recargas_apos_1"]:
        falhas.append("%d recarga(s) apos o passo 1" % out["recargas_apos_1"])
    if num_ctx and out["prompt_max"] > PORTAO["prompt_frac_max"] * num_ctx:
        falhas.append("prompt max %d > %.0f%% de %d" % (out["prompt_max"], 100 * PORTAO["prompt_frac_max"], num_ctx))
    if out["thinking_frac"] > PORTAO["thinking_frac_max"]:
        falhas.append("raciocinio %.0f%% do gerado" % (100 * out["thinking_frac"]))
    if out["tps"] is not None and out["tps"] < PORTAO["tps_min"]:
        falhas.append("%.1f tok/s" % out["tps"])
    out["portao_falhas"] = falhas
    out["passou_portao"] = not falhas
    return out


# ------------------------------------------------------------------- main
async def principal(a) -> int:
    if comum.gpu_reservada():
        print("Interruptor de GPU DESLIGADO (%s). Nada foi carregado." % comum.gpu_reservada())
        return 3
    ocup = gpu_ocupada()
    if ocup and not a.ignorar_gpu_ocupada:
        print("GPU ocupada: %s. Nada foi carregado." % ocup)
        return 3
    if embed_recente() and not a.ignorar_gpu_ocupada:
        print("Houve /api/embed nos ultimos 2 min (lumen indexando na GPU): espere e tente de novo.")
        return 3
    try:
        tools, grupo_de = await schemas()
    except Exception as e:  # noqa: BLE001
        print("Ponte lilo-host indisponivel em %s (%s): .\\lilo.ps1 ponte up" % (PONTE, e))
        return 2
    if not token_exec(gerar=False) or "executar_python" not in grupo_de:
        print("Sem token do exec/codigo ou grupos ausentes: suba a ponte com lilo.ps1 ponte up")
        return 2
    if a.ferramentas == "atual":
        tools = [t for t in tools if grupo_de[t["function"]["name"]] != "codigo"]
    elif a.ferramentas == "novas":
        tools = [t for t in tools if grupo_de[t["function"]["name"]] in ("codigo", "analise")]
    print("tools no prompt: %d (%s)" % (len(tools), a.ferramentas))
    run_id = time.strftime("%Y%m%d-%H%M%S")
    base = comum.TRABALHO / "bench" / run_id
    SAIDA.mkdir(parents=True, exist_ok=True)
    salvar = (SAIDA / "agente" / run_id) if a.salvar_transcricao else None
    saida = SAIDA / "agente.jsonl"
    todos_passaram = True
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as cli:
        versao = (await cli.get(f"{OLLAMA}/api/version")).json().get("version", "?")
        for modelo in a.modelos:
            try:
                info = await info_modelo(cli, modelo)
            except httpx.HTTPError as e:
                print("modelo %s: %s" % (modelo, e))
                todos_passaram = False
                continue
            think = _think(modelo, info["capacidades"])
            print("\n== %s (think=%s) ==" % (modelo, think))
            try:
                prefill = await calibrar_prefill(cli, modelo, think)
            except httpx.HTTPError as e:
                print("  calibracao falhou: %s" % e)
                prefill = 0.0
            ps = await ps_modelo(cli, modelo)
            print("  prefill %.0f tok/s | context %s | vram %s/%s" % (prefill, ps.get("context_length"),
                                                                     ps.get("size_vram"), ps.get("size")))
            runs: list[dict] = []
            for tarefa in a.tarefas:
                for rep in range(1, a.repeticoes + 1):
                    pasta = base / modelo / tarefa / str(rep)
                    gab = preparar(tarefa, pasta)
                    run = Run(modelo, tarefa, rep, run_id)
                    t0 = time.perf_counter()
                    await rodar_run(cli, run, gab["pedido"], tools, grupo_de, think, a.max_passos, prefill, salvar)
                    total = time.perf_counter() - t0
                    pontos, faltas = pontuar(tarefa, pasta, gab, run.resposta, run.trans)
                    linha = {"tipo": "run", "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "run_id": run_id,
                             "ollama": versao, "modelo": modelo, "digest": info["digest"], "ferramentas": a.ferramentas,
                             "tarefa": tarefa, "rep": rep, "passos": run.passos, "n_passos": len(run.passos),
                             "tool_calls": len(run.trans), "tempo_total_s": round(total, 1),
                             "tempo_tools_s": round(run.tempo_tools, 1), "falhas": run.falhas, "pontos": pontos,
                             "passou": pontos >= 3, "faltas": faltas, "motivo": run.motivo,
                             "resposta": run.resposta[:600], "context_length": ps.get("context_length")}
                    runs.append(linha)
                    with saida.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
                    print("  %-12s #%d  %d/4 %-6s %5.0f s  %2d passos  %2d tools  %s%s" % (
                        tarefa, rep, pontos, "ok" if pontos >= 3 else "FALHOU", total, len(run.passos),
                        len(run.trans), run.motivo, ("  faltou: " + "; ".join(faltas)) if faltas else ""))
                    if comum.gpu_reservada():
                        print("Interruptor desligou no meio: parando (parcial gravado).")
                        return 3
            res = resumo_modelo(modelo, runs, ps.get("context_length") or info.get("num_ctx"))
            res.update({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "run_id": run_id, "ollama": versao,
                        "digest": info["digest"], "ferramentas": a.ferramentas, "prefill_tps": round(prefill)})
            with saida.open("a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            print("  RESUMO %s: %d/%d aprovadas %s | passo mediano %s s | reuso %s | %s tok/s | PORTAO %s" % (
                modelo, res["aprovadas"], res["runs"], res["por_tarefa"], res["mediana_passo_s"], res["reuso_medio"],
                res["tps"], "PASSOU" if res["passou_portao"] else "FALHOU - " + "; ".join(res["portao_falhas"])))
            todos_passaram = todos_passaram and res["passou_portao"]
            if a.descarregar:
                with_ = await cli.post(f"{OLLAMA}/api/generate", json={"model": modelo, "keep_alive": 0})
                _ = with_.status_code
    return 0 if (a.sem_portao or todos_passaram) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modelos", default="lilo", help="lista separada por virgula (nomes do Ollama)")
    ap.add_argument("--tarefas", default=",".join(TAREFAS))
    ap.add_argument("--repeticoes", type=int, default=3)
    ap.add_argument("--ferramentas", choices=("atual", "novas", "ambas"), default="ambas")
    ap.add_argument("--max-passos", type=int, default=12)
    ap.add_argument("--salvar-transcricao", action="store_true")
    ap.add_argument("--sem-portao", action="store_true")
    ap.add_argument("--sem-descarregar", dest="descarregar", action="store_false")
    ap.add_argument("--ignorar-gpu-ocupada", action="store_true", help="so para depurar o bench")
    a = ap.parse_args()
    a.modelos = [m.strip() for m in a.modelos.split(",") if m.strip()]
    a.tarefas = [t.strip() for t in a.tarefas.split(",") if t.strip()]
    ruins = [t for t in a.tarefas if t not in TAREFAS]
    if ruins:
        print("tarefas desconhecidas: %s (validas: %s)" % (ruins, ", ".join(TAREFAS)))
        return 2
    return asyncio.run(principal(a))


if __name__ == "__main__":
    sys.exit(main())
