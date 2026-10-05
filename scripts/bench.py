"""Bench de latencia do LILO v14 — mede pelo mesmo caminho que o dono usa.

    python scripts\\bench.py --alvo ollama --n 10
    python scripts\\bench.py --alvo webui  --n 10

Alvos:
  ollama  API nativa do Ollama (/api/chat), modelo `lilo`, think desligado.
  webui   API do Open WebUI (/api/chat/completions) — e o caminho real da
          interface, com tudo o que ela acrescenta. Sem conta nem chave: o
          compose roda sem login e o bench pega o token do usuario unico.

Por pergunta mede: tempo ate o 1o token (TTFT), tempo total, tokens de prompt,
tokens gerados e tok/s. A 1a chamada e aquecimento (carrega o modelo) e fica
fora da estatistica.

Portao (codigo de saida 1 se falhar): TTFT p95 < 1,0 s, vazao >= 25 tok/s, sem
thinking e sem recarga de modelo no meio da bateria.

Respeita o interruptor de GPU do dono (~/.ollama_delegate/switch.json): com ele
em off nao carrega modelo nenhum (codigo de saida 3).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SWITCH = Path(os.environ.get("OLLAMA_DELEGATE_DIR",
                             str(Path.home() / ".ollama_delegate"))) / "switch.json"
SAIDA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LILO" / "bench"

PERGUNTAS = (
    "Quanto é 2+2?",
    "Qual é a capital do Brasil?",
    "Quanto é 7 vezes 8?",
    "Responda só com a palavra: ok",
    "Quantos dias tem uma semana?",
    "Qual é o plural de 'pão'?",
    "Quanto é 100 dividido por 4?",
    "Qual é a fórmula química da água?",
    "Quanto é 15 menos 6?",
    "Em que continente fica o Brasil?",
)
VAZAO = "Explique em um parágrafo de cerca de 150 palavras o que é PCR."


def _interruptor() -> dict:
    try:
        return json.loads(SWITCH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"estado": "on"}


def _env(chave: str) -> str:
    """Le uma chave do ambiente ou do .env do repo, sem imprimir o valor."""
    if os.environ.get(chave):
        return os.environ[chave]
    arq = ROOT / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            if linha.strip().startswith(f"{chave}="):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _token_sem_login(base: str) -> str:
    """Token do usuario unico do Open WebUI (o compose roda com WEBUI_AUTH=False).

    Nesse modo o /signin ignora e-mail e senha e devolve a sessao do usuario do
    sistema: nao ha conta para criar nem chave para colar.
    """
    try:
        r = httpx.post(f"{base}/api/v1/auths/signin",
                       json={"email": "", "password": ""}, timeout=10.0)
        return r.json().get("token", "") if r.status_code == 200 else ""
    except Exception:  # noqa: BLE001
        return ""


def _ollama(cli: httpx.Client, base: str, modelo: str, pergunta: str,
            max_tokens: int | None) -> dict:
    corpo: dict = {"model": modelo, "stream": True, "think": False,
                   "messages": [{"role": "user", "content": pergunta}]}
    if max_tokens:
        corpo["options"] = {"num_predict": max_tokens}  # nao e opcao de runner
    t0 = time.perf_counter()
    ttft = None
    pensou = False
    fim: dict = {}
    with cli.stream("POST", f"{base}/api/chat", json=corpo) as r:
        r.raise_for_status()
        for linha in r.iter_lines():
            if not linha:
                continue
            d = json.loads(linha)
            msg = d.get("message") or {}
            if msg.get("thinking"):
                pensou = True
            if ttft is None and msg.get("content"):
                ttft = time.perf_counter() - t0
            if d.get("done"):
                fim = d
    total = time.perf_counter() - t0
    ev, evd = fim.get("eval_count", 0), fim.get("eval_duration", 0)
    return {"ttft": ttft if ttft is not None else total, "total": total,
            "carga": fim.get("load_duration", 0) / 1e9,
            "tok_prompt": fim.get("prompt_eval_count", 0),
            "tok_saida": ev, "tps": (ev / (evd / 1e9)) if evd else 0.0,
            "pensou": pensou}


def _webui(cli: httpx.Client, base: str, modelo: str, pergunta: str,
           max_tokens: int | None) -> dict:
    corpo: dict = {"model": modelo, "stream": True,
                   "messages": [{"role": "user", "content": pergunta}]}
    if max_tokens:
        corpo["max_tokens"] = max_tokens
    t0 = time.perf_counter()
    ttft = None
    pensou = False
    uso: dict = {}
    pedacos = 0
    with cli.stream("POST", f"{base}/api/chat/completions", json=corpo) as r:
        r.raise_for_status()
        for linha in r.iter_lines():
            if not linha.startswith("data:"):
                continue
            dado = linha[5:].strip()
            if dado == "[DONE]":
                break
            try:
                d = json.loads(dado)
            except json.JSONDecodeError:
                continue
            if d.get("usage"):
                uso = d["usage"]
            for ch in d.get("choices") or []:
                delta = ch.get("delta") or {}
                if delta.get("reasoning_content"):
                    pensou = True
                if delta.get("content"):
                    pedacos += 1
                    if ttft is None:
                        ttft = time.perf_counter() - t0
    total = time.perf_counter() - t0
    ev = uso.get("eval_count") or uso.get("completion_tokens") or pedacos
    evd = uso.get("eval_duration", 0)
    tps = (ev / (evd / 1e9)) if evd else ev / max(total - (ttft or 0.0), 1e-6)
    return {"ttft": ttft if ttft is not None else total, "total": total,
            "carga": uso.get("load_duration", 0) / 1e9,
            "tok_prompt": uso.get("prompt_eval_count") or uso.get("prompt_tokens") or 0,
            "tok_saida": ev, "tps": tps, "pensou": pensou}


def _pct(valores: list[float], p: float) -> float:
    """Percentil pelo posto mais proximo (com 10 amostras, p95 = a pior)."""
    v = sorted(valores)
    return v[max(0, math.ceil(p * len(v)) - 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Bench de latencia do LILO")
    ap.add_argument("--alvo", choices=("ollama", "webui"), default="ollama")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--modelo", default="lilo")
    ap.add_argument("--url", default="")
    ap.add_argument("--limite-ttft", type=float, default=1.0)
    ap.add_argument("--min-tps", type=float, default=25.0)
    ap.add_argument("--max-prompt", type=int, default=0,
                    help="falha se os tokens de prompt passarem disto (0 = nao checa)")
    ap.add_argument("--sem-portao", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sw = _interruptor()
    if sw.get("estado", "on") != "on" and not a.modelo.endswith("-cloud"):
        print(f"Interruptor de GPU DESLIGADO desde {sw.get('em', '?')} "
              f"({sw.get('motivo', '')}). Nada foi carregado.")
        return 3

    if a.alvo == "ollama":
        base = (a.url or "http://127.0.0.1:11434").rstrip("/")
        cabec, chamar = {}, _ollama
    else:
        base = (a.url or _env("OWUI_URL") or "http://127.0.0.1:3000").rstrip("/")
        chave = _env("OWUI_API_KEY") or _token_sem_login(base)
        if not chave:
            print(f"Sem acesso ao Open WebUI em {base}: ele esta no ar? (.\\lilo.ps1 status)")
            return 2
        cabec, chamar = {"Authorization": f"Bearer {chave}"}, _webui

    linhas: list[dict] = []
    try:
        with httpx.Client(headers=cabec,
                          timeout=httpx.Timeout(300.0, connect=10.0)) as cli:
            aq = chamar(cli, base, a.modelo, "Responda só: pronto", None)
            print(f"aquecimento: {aq['total']:.1f}s (carga {aq['carga']:.1f}s)")
            for i in range(a.n):
                m = chamar(cli, base, a.modelo, PERGUNTAS[i % len(PERGUNTAS)], None)
                linhas.append(m)
                print(f"  {i + 1:>2}  ttft {m['ttft']:.2f}s  total {m['total']:.2f}s  "
                      f"prompt {m['tok_prompt']:>4} tok  saida {m['tok_saida']:>3} tok"
                      + ("  [PENSOU]" if m["pensou"] else ""))
            vz = chamar(cli, base, a.modelo, VAZAO, 256)
    except httpx.HTTPError as e:
        print(f"Falha de conexao com {base}: {e}")
        return 2

    ttfts = [m["ttft"] for m in linhas]
    resumo = {
        "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "alvo": a.alvo,
        "modelo": a.modelo, "n": a.n,
        "aquecimento_s": round(aq["total"], 2), "carga_s": round(aq["carga"], 2),
        "ttft_p50": round(_pct(ttfts, 0.50), 3),
        "ttft_p95": round(_pct(ttfts, 0.95), 3),
        "ttft_max": round(max(ttfts), 3),
        "tok_prompt_max": max(m["tok_prompt"] for m in linhas),
        "tps": round(vz["tps"], 1), "tok_vazao": vz["tok_saida"],
        "pensou": any(m["pensou"] for m in linhas),
        "recargas": sum(1 for m in linhas if m["carga"] > 1.0),
    }
    falhas = []
    if resumo["ttft_p95"] >= a.limite_ttft:
        falhas.append(f"TTFT p95 {resumo['ttft_p95']}s >= {a.limite_ttft}s")
    if resumo["tps"] < a.min_tps:
        falhas.append(f"vazao {resumo['tps']} tok/s < {a.min_tps}")
    if resumo["pensou"]:
        falhas.append("o modelo pensou (think deveria estar desligado)")
    if resumo["recargas"]:
        falhas.append(f"{resumo['recargas']} recarga(s) de modelo durante a bateria")
    if a.max_prompt and resumo["tok_prompt_max"] > a.max_prompt:
        falhas.append(f"prompt de {resumo['tok_prompt_max']} tokens > {a.max_prompt}")
    resumo["passou"] = not falhas

    SAIDA.mkdir(parents=True, exist_ok=True)
    with (SAIDA / "bench.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(resumo, ensure_ascii=False) + "\n")

    print(f"\n{a.alvo}/{a.modelo}: TTFT p50 {resumo['ttft_p50']}s  p95 {resumo['ttft_p95']}s  "
          f"max {resumo['ttft_max']}s | {resumo['tps']} tok/s | "
          f"prompt max {resumo['tok_prompt_max']} tok")
    print("PORTAO: " + ("PASSOU" if not falhas else "FALHOU — " + "; ".join(falhas)))
    return 0 if (a.sem_portao or not falhas) else 1


if __name__ == "__main__":
    sys.exit(main())
