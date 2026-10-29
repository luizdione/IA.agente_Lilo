"""Delegacao headless ao LILO Code: roda o OpenCode sem interface numa pasta e resume o que fez.

    python scripts\\code_run.py <pasta> "<tarefa>" [--agent build|ciencia] [--auto] [--timeout 900]
    (ou: .\\lilo.ps1 code-run <pasta> "<tarefa>")

Usa `opencode run --format json` com o modelo `lilo-code` (opencode/opencode.json) e permissoes
EXPLICITAS por OPENCODE_PERMISSION: no headless, tudo que fosse "ask" e rejeitado em silencio, entao
o padrao aqui e editar sim, shell so pytest/git diff, nada de internet; `--auto` libera o bash.
Saida: resumo em texto (tokens, arquivos tocados, `git diff --stat`, texto final, erros) e o NDJSON
bruto em %LOCALAPPDATA%\\LILO\\bench\\code\\<ts>.jsonl. Codigos: 0 ok, 1 erro do agente, 2 infra, 3 GPU.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from lilo_host import comum  # noqa: E402

SAIDA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LILO" / "bench" / "code"
PERMISSAO_PADRAO = {"edit": "allow", "external_directory": "deny", "webfetch": "deny", "websearch": "deny",
                    "task": "deny", "todowrite": "deny",
                    "bash": {"*": "deny", "git status*": "allow", "git diff*": "allow", "git log*": "allow",
                             "pytest*": "allow", "python -m pytest*": "allow"}}
PERMISSAO_AUTO = {**PERMISSAO_PADRAO, "bash": {"*": "allow", "git push*": "deny"}}
RAIZES = (r"C:\GitHub", r"E:\data", str(Path.home() / "OneDrive" / "Data_Science" / "Projetos"))


def _git(pasta: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _achar(d, chaves: tuple[str, ...]):
    """Primeiro valor de uma das chaves, em qualquer profundidade (formato do NDJSON pode mudar)."""
    if isinstance(d, dict):
        for k in chaves:
            if k in d and isinstance(d[k], (str, int, float)):
                return d[k]
        for v in d.values():
            r = _achar(v, chaves)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _achar(v, chaves)
            if r is not None:
                return r
    return None


def resumir(linhas: list[dict]) -> dict:
    tokens = {"input": 0, "output": 0, "reasoning": 0, "cache": 0}
    arquivos: list[str] = []
    textos: list[str] = []
    erros: list[str] = []
    passos = 0
    for ev in linhas:
        t = ev.get("type")
        part = ev.get("part") or {}
        if t == "step_finish":
            passos += 1
            for k, v in (part.get("tokens") or {}).items():
                if k in tokens and isinstance(v, (int, float)):
                    tokens[k] += int(v)
                elif k == "cache" and isinstance(v, dict):
                    tokens["cache"] += int(v.get("read", 0) or 0)
        elif t == "tool_use":
            tool = str(part.get("tool") or _achar(part, ("tool", "name")) or "")
            if tool in ("edit", "write", "apply_patch", "patch"):
                caminho = _achar(part.get("state") or part, ("filePath", "path", "file"))
                if caminho and str(caminho) not in arquivos:
                    arquivos.append(str(caminho))
        elif t == "text":
            txt = part.get("text") or ""
            if txt:
                textos.append(txt)
        elif t == "error":
            erros.append(json.dumps(ev.get("error") or part or ev, ensure_ascii=False)[:300])
    return {"passos": passos, "tokens": tokens, "arquivos": arquivos, "texto": "\n".join(textos).strip(), "erros": erros}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pasta")
    ap.add_argument("tarefa")
    ap.add_argument("--agent", default="build", choices=("build", "ciencia"))
    ap.add_argument("--auto", action="store_true", help="libera o bash (menos git push)")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    motivo = comum.gpu_reservada()
    if motivo:
        print("Interruptor de GPU DESLIGADO (%s). Nada foi carregado." % motivo)
        return 3
    pasta = Path(a.pasta).resolve()
    if not pasta.is_dir():
        print("pasta nao existe: %s" % pasta)
        return 2
    if not any(str(pasta).lower().startswith(r.lower()) for r in RAIZES):
        print("pasta fora de %s: %s" % (", ".join(RAIZES), pasta))
        return 2
    exe = shutil.which("opencode")
    if not exe:
        print("OpenCode nao encontrado no PATH. Instale uma vez:  npm install -g opencode-ai@1.19.5")
        return 2
    antes = _git(pasta, "status", "--porcelain")
    env = dict(os.environ)
    env.update({"OPENCODE_CONFIG": str(ROOT / "opencode" / "opencode.json"),
                "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_CLAUDE_CODE_PROMPT": "1",
                "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1", "PYTHONUTF8": "1",
                # medido 28/10: sem estas duas o primeiro `opencode run` travou 120 s (models.dev / LSP)
                "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
                "OPENCODE_PERMISSION": json.dumps(PERMISSAO_AUTO if a.auto else PERMISSAO_PADRAO),
                "LILO_HOST_TOKEN": comum.token_exec(gerar=False)})
    base = Path(sys.executable).parent
    env["PATH"] = os.pathsep.join([str(base), str(base / "Scripts")] + [env.get("PATH", "")])
    cmd = [exe, "run", "--format", "json", "--dir", str(pasta), "--agent", a.agent, a.tarefa]
    ts = time.strftime("%Y%m%d-%H%M%S")
    SAIDA.mkdir(parents=True, exist_ok=True)
    bruto = SAIDA / f"{ts}.jsonl"
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=str(pasta), env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=a.timeout)
    except subprocess.TimeoutExpired as e:
        bruto.write_text((e.stdout or "") if isinstance(e.stdout, str) else "", encoding="utf-8")
        print("tempo limite de %d s estourado; parcial em %s" % (a.timeout, bruto))
        return 1
    bruto.write_text((r.stdout or "") + ("\n--- stderr ---\n" + r.stderr if r.stderr else ""), encoding="utf-8")
    linhas = []
    for ln in (r.stdout or "").splitlines():
        ln = ln.strip()
        if ln.startswith("{"):
            try:
                linhas.append(json.loads(ln))
            except ValueError:
                pass
    res = resumir(linhas)
    depois = _git(pasta, "status", "--porcelain")
    stat = _git(pasta, "diff", "--stat")
    print("LILO Code (%s, agente %s) em %.0f s | passos %d | tokens entrada %d saida %d cache %d" % (
        pasta, a.agent, time.perf_counter() - t0, res["passos"], res["tokens"]["input"], res["tokens"]["output"],
        res["tokens"]["cache"]))
    if res["arquivos"]:
        print("arquivos tocados: " + ", ".join(res["arquivos"]))
    if stat:
        print("git diff --stat:\n" + stat)
    elif antes != depois:
        print("git status mudou:\n" + depois)
    if res["texto"]:
        print("--- resposta ---\n" + res["texto"][-3000:])
    if res["erros"]:
        print("--- erros ---\n" + "\n".join(res["erros"]))
    print("NDJSON: %s" % bruto)
    return 0 if (r.returncode == 0 and not res["erros"]) else 1


if __name__ == "__main__":
    sys.exit(main())
