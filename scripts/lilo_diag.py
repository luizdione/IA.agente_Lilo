#!/usr/bin/env python
r"""
scripts/lilo_diag.py
====================
Diagnostico rapido do LILO -- roda no Windows nativo com:

    python scripts\lilo_diag.py

Verifica:
  1. Sintaxe (ast.parse) dos 4 arquivos criticos
  2. Import de lilo_skills (CORE_SKILLS + _CORE_SKILL_META)
  3. Import de lilo (todos os subagentes)
  4. list_all_tools() -- conta tools registradas
  5. get_full_registry() -- conta skills no menu /
  6. Caches stale (__pycache__) -- avisa se houver

Saida amigavel para ajudar a identificar onde o dashboard esta falhando.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OK = "[OK]  "
FAIL = "[FAIL]"
WARN = "[WARN]"


def step(num: int, title: str) -> None:
    print(f"\n--- {num}. {title} ---")


def check_ast() -> int:
    failures = 0
    files = [
        "dashboard.py",
        "lilo.py",
        "lilo_mcp.py",
        "lilo_skills/__init__.py",
    ]
    step(1, "Sintaxe (ast.parse)")
    for rel in files:
        p = ROOT / rel
        if not p.exists():
            print(f"{FAIL} {rel}: arquivo nao existe")
            failures += 1
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"{OK} {rel} ({p.stat().st_size:,} bytes, "
                  f"{len(p.read_text(encoding='utf-8').splitlines())} linhas)")
        except SyntaxError as e:
            print(f"{FAIL} {rel}: SyntaxError linha {e.lineno}: {e.msg}")
            failures += 1
    return failures


def check_pycache() -> int:
    step(2, "Caches stale (__pycache__)")
    caches = list(ROOT.glob("**/__pycache__"))
    if not caches:
        print(f"{OK} sem __pycache__")
        return 0
    print(f"{WARN} {len(caches)} __pycache__ encontradas. "
          "Se o dashboard estiver com erro stale, remova-as:")
    for c in caches[:5]:
        rel = c.relative_to(ROOT)
        print(f"       {rel}")
    if len(caches) > 5:
        print(f"       ... ({len(caches) - 5} mais)")
    print()
    print("       Comando para limpar:")
    print("       Get-ChildItem -Path . -Filter __pycache__ -Recurse | "
          "Remove-Item -Recurse -Force")
    return 0  # warning, nao bloqueante


def check_lilo_skills() -> int:
    step(3, "Import lilo_skills (menu / do dashboard)")
    try:
        from lilo_skills import (
            CORE_SKILLS, _CORE_SKILL_META, get_full_registry,
        )
        print(f"{OK} CORE_SKILLS: {len(CORE_SKILLS)} entradas")
        print(f"{OK} _CORE_SKILL_META: {len(_CORE_SKILL_META)} entradas")
        if len(CORE_SKILLS) != len(_CORE_SKILL_META):
            print(f"{WARN} CORE_SKILLS e _CORE_SKILL_META com tamanhos "
                  "diferentes -- pode causar nomes faltando no menu")
        reg = get_full_registry()
        total = reg.get("total_skills", 0)
        core = reg.get("core_skills", 0)
        print(f"{OK} get_full_registry: {total} skills total ({core} core + "
              f"{total - core} geradas)")
        # Validar presenca das 8 novas v10.2
        names = {s["name"] for s in reg["skills"]}
        novas = [
            "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
            "lilo_memory_delete", "lilo_cost_today", "lilo_cost_recent",
            "lilo_pull_model", "lilo_list_local_models",
        ]
        faltando = [n for n in novas if n not in names]
        if faltando:
            print(f"{FAIL} faltando no menu: {faltando}")
            return 1
        print(f"{OK} todas as 8 novas tools v10.2 presentes no menu")
        return 0
    except Exception as e:
        print(f"{FAIL} erro: {type(e).__name__}: {e}")
        return 1


def check_lilo() -> int:
    step(4, "Import lilo (subagentes + tools)")
    try:
        import lilo
        tools = lilo.list_all_tools()
        print(f"{OK} list_all_tools: {len(tools)} tools registradas")
        names = {t["name"] for t in tools}
        novas = [
            "lilo_memory_set", "lilo_memory_get", "lilo_memory_list",
            "lilo_memory_delete", "lilo_cost_today", "lilo_cost_recent",
            "lilo_pull_model", "lilo_list_local_models",
        ]
        faltando = [n for n in novas if n not in names]
        if faltando:
            print(f"{FAIL} faltando em list_all_tools: {faltando}")
            return 1
        print(f"{OK} todas as 8 novas tools v10.2 presentes em "
              "list_all_tools (Claude Desktop deve mostra-las apos reiniciar)")
        return 0
    except Exception as e:
        print(f"{FAIL} erro: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


def check_kv_memory() -> int:
    step(5, "KV memory (data/kv_memory.db)")
    try:
        from shared.kv_memory import get_memory
        m = get_memory()
        m.set("__diag_test__", "ok", ns="diag")
        v = m.get("__diag_test__", ns="diag")
        m.delete("__diag_test__", ns="diag")
        if v == "ok":
            print(f"{OK} kv_memory funcional")
            return 0
        print(f"{FAIL} kv_memory leu valor errado: {v!r}")
        return 1
    except Exception as e:
        msg = str(e)
        if "disk I/O error" in msg or "database is locked" in msg:
            print(f"{WARN} {type(e).__name__}: {e}")
            print("       OneDrive lock no DB SQLite. Sugerido:")
            print("       1. Pause OneDrive sync para a pasta memory/")
            print("       2. Ou mova memory/kv_memory.db para fora do OneDrive")
            print("          e atualize DB_PATH em shared/kv_memory.py")
            return 0  # warning
        print(f"{FAIL} {type(e).__name__}: {e}")
        return 1


def main() -> int:
    print(f"LILO Diagnostico -- root: {ROOT}")
    failures = 0
    failures += check_ast()
    check_pycache()
    failures += check_lilo_skills()
    failures += check_lilo()
    failures += check_kv_memory()
    print()
    if failures == 0:
        print("=" * 50)
        print(f"{OK} TUDO OK -- dashboard e Claude Desktop devem funcionar")
        print("=" * 50)
        print()
        print("Se ainda esta com erro:")
        print("  1. Feche o dashboard (Ctrl+C) e rode START_LILO_WINDOWS.bat")
        print("  2. Saia do Claude Desktop pela bandeja do sistema (nao basta")
        print("     fechar a janela) e reabra")
        print("  3. Limpe __pycache__ se houver:")
        print("     Get-ChildItem -Path . -Filter __pycache__ -Recurse | "
              "Remove-Item -Recurse -Force")
        return 0
    print("=" * 50)
    print(f"{FAIL} {failures} problema(s) detectado(s)")
    print("=" * 50)
    return 1


if __name__ == "__main__":
    sys.exit(main())
