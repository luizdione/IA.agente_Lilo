#!/usr/bin/env python
"""
scripts/diagnostico_lilo.py — Auditoria/diagnóstico do LILO em todos os níveis.
================================================================================
V18.2 (skill /diagnostico_lilo). DETERMINÍSTICO e OFFLINE-SAFE: zero chamadas
LLM — o objetivo é fazer a varredura pesada de graça e entregar um relatório
COMPACTO para o Claude (Code/Desktop) transformar em plano de correção sem
gastar tokens re-explorando o repositório.

Níveis auditados:
  A. codigo    — sintaxe (compile) + pytest offline (pule com --fast)
  B. fiacao    — registro de agentes importa? keyword-map órfão? tools dos
                 profiles existem no lilo_mcp? (classe de bug "paper fantasma")
  C. envs      — .env.example vs leituras reais no código (canais mortos)
  D. runtime   — Ollama/LiteLLM/Anthropic/custo/memória (best-effort, 1.5s;
                 indisponível = INFO, não erro — pule com --no-runtime)
  E. docs      — drift de versão README vs CHANGELOG

Saída: markdown compacto no stdout (limitado por seção) + JSON completo com
--json PATH. Exit code: 2 se houver P0, 1 se houver P1, senão 0.

Uso:
    python scripts/diagnostico_lilo.py                 # tudo
    python scripts/diagnostico_lilo.py --fast          # sem pytest
    python scripts/diagnostico_lilo.py --no-runtime    # sem checks de rede
    python scripts/diagnostico_lilo.py --json diag.json
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKIP_DIRS = ("__pycache__", "_ARCHIVE", ".venv", ".git", "node_modules")
ENV_PREFIXES = ("LILO_", "OLLAMA_", "VILLA_", "ANTHROPIC", "LITELLM",
                "SCHOLAR_", "NCBI", "SEMANTIC_", "GOOGLE_", "PDF_", "LLM_")
MAX_LINES_PER_SECTION = 20  # teto de linhas exibidas por seção (resto no JSON)

FINDINGS: list[dict] = []


def add(nivel: str, area: str, fid: str, msg: str) -> None:
    FINDINGS.append({"nivel": nivel, "area": area, "id": fid, "msg": msg})


def _pyfiles() -> list[Path]:
    return [p for p in ROOT.rglob("*.py")
            if not any(s in str(p) for s in SKIP_DIRS)]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# ── A. Código ────────────────────────────────────────────────────────────────

def check_codigo(fast: bool) -> None:
    n_err = 0
    for p in _pyfiles():
        src = _read(p)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                compile(src, str(p), "exec")
            except SyntaxError as e:
                n_err += 1
                add("P0", "codigo", "A-SYNTAX",
                    f"{p.relative_to(ROOT)}:{e.lineno}: {e.msg}")
    if not n_err:
        add("OK", "codigo", "A-SYNTAX", "0 erros de sintaxe")
    if fast:
        add("INFO", "codigo", "A-PYTEST", "pytest PULADO (--fast)")
        return
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no",
             "-p", "no:cacheprovider"],
            cwd=ROOT, capture_output=True, text=True, timeout=900)
        tail = (r.stdout or "").strip().splitlines()
        resumo = tail[-1] if tail else "(sem saida)"
        if r.returncode == 0:
            add("OK", "codigo", "A-PYTEST", f"pytest verde: {resumo}")
        else:
            add("P0", "codigo", "A-PYTEST", f"pytest FALHOU: {resumo}")
            for ln in tail[-12:]:
                if ln.startswith("FAILED") or ln.startswith("ERROR"):
                    add("P0", "codigo", "A-PYTEST", ln[:160])
    except Exception as e:
        add("P1", "codigo", "A-PYTEST", f"pytest nao rodou: {e}")


# ── B. Fiação (registro/keywords/tools) ──────────────────────────────────────

def check_fiacao() -> None:
    lilo_src = _read(ROOT / "lilo.py")
    # Registro de agentes: tuplas ("nome", "modulo.path", "Classe") DENTRO do
    # bloco _AGENT_REGISTRY = [ ... ]. Escopar ao bloco evita casar tuplas de
    # 3 strings que aparecem em outros lugares (ex.: `if tool in ("a","b","c")`
    # nos handlers) -- falso-positivo pego pelo proprio diagnostico na V18.7.
    m_reg = re.search(r"_AGENT_REGISTRY\s*=\s*\[(.*?)\]", lilo_src, re.DOTALL)
    reg_src = m_reg.group(1) if m_reg else ""
    # o modulo tem ponto (agents.x.y); a classe termina em 'Agent' -> ancoras
    # que distinguem um registro de agente de uma tupla qualquer.
    reg = re.findall(
        r'\(\s*"(\w+)"\s*,\s*"([\w.]+\.[\w.]+)"\s*,\s*"(\w+Agent)"\s*\)',
        reg_src)
    nomes_registrados = set()
    for nome, modulo, classe in reg:
        nomes_registrados.add(nome)
        mod_dir = ROOT / modulo.replace(".agent", "").replace(".", "/")
        try:
            m = importlib.import_module(modulo)
            getattr(m, classe)
            add("OK", "fiacao", "B-REG", f"agente '{nome}' importa ({modulo})")
        except Exception as e:
            if not mod_dir.exists():
                # classe "paper fantasma": registrado mas diretório ausente
                add("P1", "fiacao", "B-REG-AUSENTE",
                    f"agente '{nome}': diretorio de {modulo} NAO existe no "
                    f"repo (registrado em lilo.py; import falha silenciosa)")
            else:
                add("P0", "fiacao", "B-REG-QUEBRADO",
                    f"agente '{nome}': modulo existe mas import FALHA: "
                    f"{str(e)[:120]}")
    # Keyword-map aponta p/ agente não registrado?
    kw_block = re.search(r"_KEYWORD_MAP\s*=\s*\{(.+?)\n\}", lilo_src, re.DOTALL)
    if kw_block:
        kw_keys = set(re.findall(r'^\s*"(\w+)":\s*\[', kw_block.group(1),
                                 re.MULTILINE))
        for k in sorted(kw_keys - nomes_registrados):
            add("P1", "fiacao", "B-KW-ORFAO",
                f"_KEYWORD_MAP tem '{k}' sem entrada no registro de agentes")
    # Tools dos profiles existem no lilo_mcp?
    mcp_src = _read(ROOT / "lilo_mcp.py")
    tools_def = set(re.findall(
        r"@_profile_tool[^\n]*\n(?:\s*#[^\n]*\n)*\s*def\s+(\w+)", mcp_src))
    try:
        import yaml
        prof = yaml.safe_load(_read(ROOT / "config" / "profiles.yaml")) or {}
        usados: set[str] = set()
        for pname, pdata in prof.items():
            if isinstance(pdata, dict):
                mt = pdata.get("mcp_tools")
                if isinstance(mt, list):
                    usados.update(str(t) for t in mt)
        fantasmas = sorted(usados - tools_def)
        for t in fantasmas:
            add("P0", "fiacao", "B-TOOL-FANTASMA",
                f"profiles.yaml expoe tool '{t}' sem definicao no lilo_mcp.py")
        if not fantasmas:
            add("OK", "fiacao", "B-TOOLS",
                f"{len(tools_def)} tools MCP definidas; profiles consistentes")
    except Exception as e:
        add("P2", "fiacao", "B-PROFILES", f"profiles.yaml nao avaliado: {e}")


# ── C. Envs (canais mortos) ──────────────────────────────────────────────────

def _interesting(v: str) -> bool:
    return v.startswith(ENV_PREFIXES)



# Envs construidas DINAMICAMENTE no codigo (ex.: "VILLA_TIER_%s" % stage) --
# um grep literal nunca as encontra; nao acusar como mortas.
DYNAMIC_ENV_PREFIXES = ("VILLA_TIER_",)


def check_envs() -> None:
    exemplo = _read(ROOT / ".env.example")
    documentadas = {m for m in re.findall(
        r"^#?\s*([A-Z][A-Z0-9_]+)=", exemplo, re.MULTILINE) if _interesting(m)}
    lidas: set[str] = set()
    # inclui wrappers do repo (_env_flag em shared/policy.py) alem dos acessos
    # diretos -- leitura via wrapper era falso-positivo de "doc morta".
    pat = re.compile(
        r"(?:get_env|getenv|environ\.get|environ\[|_env_flag)\(?\s*[\"']"
        r"([A-Z][A-Z0-9_]+)[\"']")
    for p in _pyfiles():
        if "tests" in p.parts:
            continue
        for m in pat.findall(_read(p)):
            if _interesting(m):
                lidas.add(m)
    nunca_lidas = sorted(
        v for v in documentadas - lidas
        if not v.startswith(DYNAMIC_ENV_PREFIXES))
    # filtro dinamico tambem aqui: o literal "VILLA_TIER_" capturado do
    # codigo ("VILLA_TIER_%s" % stage) nao e uma env de verdade.
    nao_documentadas = sorted(
        v for v in lidas - documentadas
        if not v.startswith(DYNAMIC_ENV_PREFIXES))
    for v in nunca_lidas:
        add("P2", "envs", "C-DOC-MORTA",
            f"{v} esta no .env.example mas NENHUM codigo a le")
    for v in nao_documentadas:
        add("P2", "envs", "C-SEM-DOC",
            f"{v} e lida pelo codigo mas nao esta no .env.example")
    add("OK" if not (nunca_lidas or nao_documentadas) else "INFO", "envs",
        "C-RESUMO", f"{len(documentadas)} documentadas | "
        f"{len(nunca_lidas)} sem leitor | {len(nao_documentadas)} sem doc")


# ── D. Runtime (best-effort; indisponivel = INFO) ────────────────────────────

def check_runtime() -> None:
    import requests
    from shared.utils import get_env
    ollama = get_env("OLLAMA_HOST", "http://localhost:11434")
    try:
        r = requests.get(ollama + "/api/tags", timeout=1.5)
        instalados = [m.get("name", "") for m in r.json().get("models", [])]
        add("OK", "runtime", "D-OLLAMA",
            f"Ollama ON ({len(instalados)} modelos)")
        from shared.llm_client import MODELS
        from shared.model_catalog import missing_models
        import os
        configurados = list(MODELS.values()) + [
            os.getenv("VILLA_WORKER_GENERAL_MODEL", "gpt-oss:120b-cloud"),
            os.getenv("LILO_SKILLSMITH_MODEL", "gpt-oss:120b-cloud"),
        ]
        for falta in missing_models(configurados, instalados):
            add("P1", "runtime", "D-MODELO-AUSENTE",
                f"modelo configurado '{falta}' NAO esta instalado no Ollama")
    except Exception:
        add("INFO", "runtime", "D-OLLAMA",
            "Ollama OFFLINE nesta maquina (checks de modelo pulados)")
    try:
        import requests as _rq
        litellm = get_env("LITELLM_PROXY_URL", "http://localhost:4000")
        _rq.get(litellm + "/health", timeout=1.5)
        add("OK", "runtime", "D-LITELLM", "LiteLLM proxy ON")
    except Exception:
        add("INFO", "runtime", "D-LITELLM", "LiteLLM proxy offline")
    try:
        import importlib.util as ilu
        tem_chave = bool(get_env("ANTHROPIC_API_KEY", ""))
        tem_pkg = ilu.find_spec("anthropic") is not None
        if tem_chave and not tem_pkg:
            add("P1", "runtime", "D-ANTHROPIC",
                "ANTHROPIC_API_KEY presente mas pacote 'anthropic' ausente")
        else:
            add("INFO", "runtime", "D-ANTHROPIC",
                f"chave={'sim' if tem_chave else 'nao'} | "
                f"pacote={'sim' if tem_pkg else 'nao'}")
    except Exception as e:
        add("P2", "runtime", "D-ANTHROPIC", f"check falhou: {e}")
    try:
        from shared.cost_tracker import CostTracker
        t = CostTracker()
        add("OK" if t.enabled else "P1", "runtime", "D-CUSTO",
            "telemetria de custo gravavel" if t.enabled
            else "telemetria de custo DESATIVADA (nenhum path gravavel)")
    except Exception as e:
        add("P1", "runtime", "D-CUSTO", f"CostTracker falhou: {e}")
    try:
        from shared.kv_memory import get_memory
        st = get_memory().stats()
        n = st.get("total_keys", st.get("total", st.get("keys", "?")))
        add("OK", "runtime", "D-MEMORIA", f"KV memoria OK ({n} chaves)")
    except Exception as e:
        add("P1", "runtime", "D-MEMORIA", f"KV memoria falhou: {e}")


# ── E. Docs (drift) ──────────────────────────────────────────────────────────

def check_docs() -> None:
    readme = _read(ROOT / "README.md")
    changelog = _read(ROOT / "docs" / "versoes" / "CHANGELOG.md")
    m_badge = re.search(r"version-([\d.]+)", readme)
    m_ch = re.search(r"^## v([\d.]+)", changelog, re.MULTILINE)
    if m_badge and m_ch:
        badge, ch = m_badge.group(1), m_ch.group(1)
        if not badge.startswith(ch):
            add("P1", "docs", "E-VERSAO",
                f"README badge v{badge} != CHANGELOG v{ch} (drift)")
        else:
            add("OK", "docs", "E-VERSAO", f"versao consistente (v{ch})")
    else:
        add("P2", "docs", "E-VERSAO", "nao consegui comparar versoes")


# ── Relatório ────────────────────────────────────────────────────────────────

def render() -> tuple[str, int]:
    ordem = {"P0": 0, "P1": 1, "P2": 2, "INFO": 3, "OK": 4}
    contagem = {k: sum(1 for f in FINDINGS if f["nivel"] == k) for k in ordem}
    linhas = ["# DIAGNOSTICO LILO (deterministico, 0 tokens)", ""]
    linhas.append(
        "**Resumo:** P0=%d | P1=%d | P2=%d | INFO=%d | OK=%d" % (
            contagem["P0"], contagem["P1"], contagem["P2"],
            contagem["INFO"], contagem["OK"]))
    linhas.append("")
    for area in ("codigo", "fiacao", "envs", "runtime", "docs"):
        sel = sorted((f for f in FINDINGS if f["area"] == area),
                     key=lambda f: ordem[f["nivel"]])
        if not sel:
            continue
        linhas.append(f"## {area}")
        for f in sel[:MAX_LINES_PER_SECTION]:
            linhas.append(f"- [{f['nivel']}][{f['id']}] {f['msg']}")
        if len(sel) > MAX_LINES_PER_SECTION:
            linhas.append(
                f"- ... (+{len(sel) - MAX_LINES_PER_SECTION} ocultos; "
                f"use --json)")
        linhas.append("")
    rc = 2 if contagem["P0"] else (1 if contagem["P1"] else 0)
    linhas.append(f"_Exit code: {rc} (2=P0, 1=P1, 0=limpo)._")
    return "\n".join(linhas), rc


def main() -> int:
    fast = "--fast" in sys.argv
    no_runtime = "--no-runtime" in sys.argv
    json_path = None
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        json_path = sys.argv[i + 1] if i + 1 < len(sys.argv) else "diagnostico_lilo.json"
    check_codigo(fast)
    check_fiacao()
    check_envs()
    if not no_runtime:
        check_runtime()
    check_docs()
    texto, rc = render()
    print(texto)
    if json_path:
        Path(json_path).write_text(
            json.dumps(FINDINGS, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\nJSON completo: {json_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
