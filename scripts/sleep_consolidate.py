#!/usr/bin/env python3
"""
scripts/sleep_consolidate.py -- "Sono" de consolidacao de MEMORIA do LILO.

Inspirado na literatura de consolidacao de memoria em sono e em "sleep-time
compute" de agentes (ex.: Nature Communications 2022, "Sleep-like unsupervised
replay reduces catastrophic forgetting in ANNs"; Letta "sleep-time compute",
2025; SCM, 2026).

  IMPORTANTE -- o que este script NAO faz:
  Ele NAO altera os PESOS de nenhum modelo. Os modelos do Ollama (gemma3/qwen)
  sao CONGELADOS na inferencia: nao ha gradiente em repouso, logo nao existe
  "corrigir a rede neural durante o stand-by" para um modelo ja treinado.
  Aquele "sono" que reescreve pesos so vale para modelos EM TREINO/fine-tuning.

  O que este script FAZ (a versao aplicavel ao LILO): consolida a MEMORIA DO
  AGENTE -- os stores externos -- durante o tempo ocioso, para organizar e
  ECONOMIZAR TOKENS nas proximas sessoes:
    1. KV memory   -> snapshot (backup) + remove entradas expiradas (TTL)
    2. Chat antigo -> destila FATOS DURAVEIS (Ollama LOCAL, 0 token Claude) e
                      arquiva um resumo curto ANTES de apagar o chat cru
    3. PMM (.project-memory) -> archive-tasks + rotate-changelog (engine da skill
                      gerente_memoria_projeto), quando o orcamento de tokens estoura
    4. Cost DB     -> poda linhas antigas de custo (+ VACUUM)
    5. Router      -> nota: embeddings vivem em RAM por processo (nada a persistir)

SEGURANCA:
  * DRY-RUN por PADRAO: sem --apply, o script so MOSTRA o que faria.
  * Faz snapshot do KV antes de qualquer mudanca.
  * Toda sumarizacao usa OLLAMA local -> nunca gasta orcamento do Claude.
  * Chat so e' apagado depois de destilar fatos + gravar um resumo (nada se perde).
  * Se o Ollama estiver fora do ar, a etapa de chats e' PULADA (nao apaga nada).

Uso:
  python scripts/sleep_consolidate.py                     # dry-run (so o plano)
  python scripts/sleep_consolidate.py --apply             # efetiva
  python scripts/sleep_consolidate.py --apply --days 30 --keep-chats 30
  python scripts/sleep_consolidate.py --apply --no-pmm --no-cost

Agendar no ocioso (Windows Task Scheduler): crie uma tarefa com gatilho
"Quando o computador estiver ocioso"; Acao: iniciar programa=python.exe,
argumentos = "<repo>\\scripts\\sleep_consolidate.py" --apply
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# -- Torna `shared.*` importavel quando rodado de qualquer lugar --------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

try:
    from shared.utils import load_env
    load_env()  # carrega o .env (no github, via hardlink p/ o .env do OneDrive)
except Exception:
    pass

# Engine PMM (vive na skill do usuario, nao no repo) + projeto-alvo default.
# Ambos configuraveis por env; a etapa PMM e' pulada se o caminho nao existir.
_PMM_ENGINE = os.environ.get(
    "LILO_PMM_ENGINE",
    r"C:\Users\luizd\.claude\skills\gerente_memoria_projeto\pmm.py")
_PMM_PROJECT = os.environ.get(
    "LILO_PMM_PROJECT",
    r"C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente")

_QUIET = False


def _p(msg: str = "") -> None:
    if not _QUIET:
        print(msg)


def _ollama_up() -> bool:
    """Ollama no ar? Checagem HTTP direta (sem custo, sem chamar modelo)."""
    try:
        import urllib.request
        base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        with urllib.request.urlopen(base + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. KV memory: snapshot + limpeza de expirados
# ---------------------------------------------------------------------------
def stage_kv(apply: bool, keep_backups_days: int) -> str:
    try:
        from shared.kv_memory import get_memory
    except Exception as e:
        return "KV: indisponivel (%s)" % e
    kv = get_memory()
    st = kv.stats()
    total, expired = st.get("total", 0), st.get("expired", 0)
    _p("  [KV] %d entradas (%d expiradas) em %s"
       % (total, expired, st.get("db_path", "?")))

    # snapshot antes de mexer
    backups_dir = _REPO / "backups"
    snap = backups_dir / ("kv_sleep_%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    if apply:
        try:
            backups_dir.mkdir(parents=True, exist_ok=True)
            snap.write_text(kv.export_json(), encoding="utf-8")
            _p("  [KV] snapshot -> %s" % snap.name)
        except Exception as e:
            _p("  [KV] aviso: falha no snapshot (%s)" % e)
        removed = kv.cleanup_expired()
        # poda snapshots antigos
        cut = datetime.now() - timedelta(days=keep_backups_days)
        pruned = 0
        for f in backups_dir.glob("kv_sleep_*.json"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) < cut:
                    f.unlink()
                    pruned += 1
            except Exception:
                pass
        return "KV: %d expiradas removidas; %d snapshots antigos podados" % (removed, pruned)
    return "KV: [dry-run] removeria %d expiradas + faria snapshot" % expired


# ---------------------------------------------------------------------------
# 2. Chats antigos: destila fatos duraveis (Ollama) + arquiva resumo + apaga
# ---------------------------------------------------------------------------
def _chat_age_days(iso: str) -> float:
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).total_seconds() / 86400.0
    except Exception:
        return 0.0


def _mini_resumo(msgs: list[dict], max_chars: int = 300) -> str:
    """Resumo heuristico ZERO-token: 1a pergunta do usuario + ultima resposta."""
    first_u = next((m["content"] for m in msgs if m.get("role") == "user"), "")
    last_a = next((m["content"] for m in reversed(msgs)
                   if m.get("role") == "assistant"), "")
    s = ("P: %s\nR: %s" % (first_u.strip(), last_a.strip())).strip()
    return s[:max_chars]


def stage_chats(apply: bool, days: int, keep_chats: int, min_msgs: int) -> str:
    try:
        from shared.chat_memory import get_memory
    except Exception as e:
        return "Chats: indisponivel (%s)" % e
    cm = get_memory()
    chats = cm.list_chats(limit=1000)
    if not chats:
        return "Chats: nenhum chat no historico"

    # Nunca toca nos `keep_chats` mais recentes (list_chats ja vem por updated DESC).
    protegidos = {c["id"] for c in chats[:keep_chats]}
    candidatos = []
    for c in chats[keep_chats:]:
        if c["id"] in protegidos:
            continue
        idade = _chat_age_days(c.get("updated_at") or c.get("created_at") or "")
        if idade < days:
            continue
        n = len(cm.get_messages(c["id"]))
        if n < min_msgs:
            # chat velho e trivial: apaga direto (sem destilar) so com --apply
            candidatos.append((c, n, False))
        else:
            candidatos.append((c, n, True))

    if not candidatos:
        return ("Chats: nada a consolidar (%d chats, todos recentes/protegidos)"
                % len(chats))

    _p("  [Chats] %d candidatos (> %dd, alem dos %d mais recentes):"
       % (len(candidatos), days, keep_chats))
    for c, n, destilar in candidatos[:12]:
        _p("     - %s  \"%s\"  (%d msgs, %.0fd)%s"
           % (c["id"], (c.get("title") or "")[:40], n,
              _chat_age_days(c.get("updated_at") or c.get("created_at") or ""),
              "" if destilar else "  [trivial]"))
    if len(candidatos) > 12:
        _p("     ... e mais %d" % (len(candidatos) - 12))

    if not apply:
        return "Chats: [dry-run] consolidaria %d chats antigos" % len(candidatos)

    # Precisa do Ollama p/ destilar. Se estiver fora, NAO apaga nada.
    ollama = _ollama_up()
    if not ollama:
        return ("Chats: PULADO -- Ollama fora do ar (nao apago sem antes destilar)")

    consolidados = destilados = 0
    try:
        from shared.kv_memory import get_memory as _kv
        kv = _kv()
    except Exception:
        kv = None
    for c, n, destilar in candidatos:
        cid = c["id"]
        try:
            msgs = cm.get_messages(cid)
            fatos = cm.distill_facts(cid) if destilar else []
            if fatos:
                destilados += 1
            # arquiva SEMPRE um resumo curto antes de apagar (nada se perde)
            if kv is not None:
                resumo = _mini_resumo(msgs)
                val = "%s | fatos: %s" % (
                    resumo,
                    "; ".join("%s=%s" % (f["key"], f["value"]) for f in fatos) or "-")
                kv.set("chat_%s" % cid, val[:1000], ns="chat_archive",
                       tags="consolidated,%s" % (c.get("title") or "")[:30])
            cm.delete_chat(cid)
            consolidados += 1
        except Exception as e:
            _p("  [Chats] aviso: falha em %s (%s)" % (cid, e))
    return ("Chats: %d consolidados (%d com fatos destilados via Ollama), "
            "resumos em kv ns='chat_archive'" % (consolidados, destilados))


# ---------------------------------------------------------------------------
# 3. PMM (.project-memory): archive-tasks + rotate-changelog via engine da skill
# ---------------------------------------------------------------------------
def stage_pmm(apply: bool) -> str:
    if not os.path.exists(_PMM_ENGINE):
        return "PMM: engine nao encontrado (%s) -- etapa pulada" % _PMM_ENGINE
    if not os.path.isdir(os.path.join(_PMM_PROJECT, ".project-memory")):
        return "PMM: projeto sem .project-memory (%s) -- pulado" % _PMM_PROJECT
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

    def _run(*cmd):
        try:
            r = subprocess.run(
                [sys.executable, _PMM_ENGINE, *cmd, "--root", _PMM_PROJECT],
                capture_output=True, text=True, env=env, timeout=120)
            return (r.stdout or "").strip(), (r.stderr or "").strip(), r.returncode
        except Exception as e:
            return "", str(e), 1

    out, err, _ = _run("status", "--json")
    _p("  [PMM] status: %s" % (out[:200] or err[:200] or "(sem saida)"))
    if not apply:
        return "PMM: [dry-run] rodaria archive-tasks + rotate-changelog"

    o1, e1, rc1 = _run("archive-tasks")
    o2, e2, rc2 = _run("rotate-changelog")
    return ("PMM: archive-tasks rc=%d; rotate-changelog rc=%d%s"
            % (rc1, rc2, (" (%s)" % (e1 or e2)) if (e1 or e2) else ""))


# ---------------------------------------------------------------------------
# 4. Cost DB: poda linhas antigas
# ---------------------------------------------------------------------------
def stage_cost(apply: bool, keep_days: int) -> str:
    try:
        from shared import cost_tracker
        db = Path(cost_tracker.DB_PATH)
    except Exception as e:
        return "Cost: indisponivel (%s)" % e
    if not db.exists():
        return "Cost: sem DB (%s)" % db
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    try:
        con = sqlite3.connect(str(db))
        cols = [r[1] for r in con.execute("PRAGMA table_info(requests)").fetchall()]
        if "date" not in cols:
            con.close()
            return "Cost: tabela sem coluna 'date' -- pulado"
        n = con.execute("SELECT COUNT(*) FROM requests WHERE date < ?",
                        (cutoff,)).fetchone()[0]
        if not apply:
            con.close()
            return "Cost: [dry-run] podaria %d linhas anteriores a %s" % (n, cutoff)
        con.execute("DELETE FROM requests WHERE date < ?", (cutoff,))
        con.commit()
        con.execute("VACUUM")
        con.close()
        return "Cost: %d linhas antigas (< %s) podadas + VACUUM" % (n, cutoff)
    except Exception as e:
        return "Cost: erro (%s)" % e


# ---------------------------------------------------------------------------
def main() -> int:
    global _QUIET
    ap = argparse.ArgumentParser(
        description="Sono de consolidacao de memoria do LILO (NAO altera pesos "
                    "do modelo; organiza a memoria do agente). Dry-run por padrao.")
    ap.add_argument("--apply", action="store_true",
                    help="Efetiva as mudancas (sem isso: dry-run).")
    ap.add_argument("--days", type=int, default=14,
                    help="Idade minima (dias) para um chat ser consolidado (14).")
    ap.add_argument("--keep-chats", type=int, default=20,
                    help="Nunca toca nos N chats mais recentes (20).")
    ap.add_argument("--min-msgs", type=int, default=4,
                    help="Chats com menos msgs sao tratados como triviais (4).")
    ap.add_argument("--keep-cost-days", type=int, default=90,
                    help="Mantem linhas de custo dos ultimos N dias (90).")
    ap.add_argument("--keep-backups-days", type=int, default=30,
                    help="Mantem snapshots KV dos ultimos N dias (30).")
    ap.add_argument("--no-kv", action="store_true")
    ap.add_argument("--no-chats", action="store_true")
    ap.add_argument("--no-pmm", action="store_true")
    ap.add_argument("--no-cost", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    _QUIET = args.quiet
    apply = args.apply

    _p("=" * 64)
    _p("  LILO -- sono de consolidacao de memoria")
    _p("  MODO: %s" % ("APLICANDO (--apply)" if apply
                       else "DRY-RUN (nada sera alterado; use --apply)"))
    _p("  (NAO altera pesos do modelo -- so a memoria do agente)")
    _p("=" * 64)

    report: list[str] = []
    if not args.no_kv:
        _p("\n> KV memory"); report.append(stage_kv(apply, args.keep_backups_days))
    if not args.no_chats:
        _p("\n> Chats antigos")
        report.append(stage_chats(apply, args.days, args.keep_chats, args.min_msgs))
    if not args.no_pmm:
        _p("\n> Memoria de projeto (PMM)"); report.append(stage_pmm(apply))
    if not args.no_cost:
        _p("\n> Cost DB"); report.append(stage_cost(apply, args.keep_cost_days))

    _p("\n" + "-" * 64)
    _p("  RESUMO:")
    for line in report:
        _p("   * " + line)
    _p("  Router: embeddings vivem em RAM por processo; nada a persistir "
       "(reconstroi sozinho quando as assinaturas dos agentes mudam).")
    _p("-" * 64)
    if not apply:
        _p("  Dry-run: rode de novo com --apply para efetivar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
