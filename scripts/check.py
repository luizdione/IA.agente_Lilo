#!/usr/bin/env python
"""
scripts/check.py — verificação de saúde do LILO num comando.

Roda, em ordem:
  1. py_compile de todos os .py  (erros de SINTAXE -> falha)
  2. pyflakes                    (nomes indefinidos -> falha; imports/vars não
                                  usados -> apenas avisa, pois há probes
                                  try/except intencionais)
  3. pytest                      (testes -> falha)

Uso:
    python scripts/check.py            # tudo
    python scripts/check.py --no-tests # pula pytest (rápido)

Exit 0 = saudável. Requer pyflakes e pytest (já em requirements de dev).
"""
from __future__ import annotations
import subprocess, sys, warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("__pycache__", "_ARCHIVE", ".venv")


def pyfiles():
    return [p for p in ROOT.rglob("*.py") if not any(s in str(p) for s in SKIP)]


def step_syntax(files):
    errs = []
    for p in files:
        src = p.read_text(encoding="utf-8", errors="ignore")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                compile(src, str(p), "exec")
            except SyntaxError as e:
                errs.append(f"{p.relative_to(ROOT)}:{e.lineno}: {e.msg}")
            for x in w:
                if "invalid escape" in str(x.message):
                    errs.append(f"{p.relative_to(ROOT)}:{x.lineno}: {x.message}")
    return errs


def step_pyflakes(files):
    res = subprocess.run([sys.executable, "-m", "pyflakes"] + [str(p) for p in files],
                         capture_output=True, text=True)
    undef, minor = [], 0
    for line in res.stdout.splitlines():
        if "undefined name" in line or "referenced before assignment" in line:
            undef.append(line.replace(str(ROOT) + "\\", "").replace("\\", "/"))
        elif ":" in line:
            minor += 1
    return undef, minor


def main():
    run_tests = "--no-tests" not in sys.argv
    files = pyfiles()
    ok = True

    print(f"[1/3] Sintaxe + escapes ({len(files)} arquivos)...", end=" ")
    errs = step_syntax(files)
    if errs:
        ok = False
        print(f"FALHOU ({len(errs)})")
        for e in errs[:20]:
            print("   ", e)
    else:
        print("OK")

    print("[2/3] pyflakes...", end=" ")
    undef, minor = step_pyflakes(files)
    if undef:
        ok = False
        print(f"FALHOU — {len(undef)} nomes indefinidos")
        for u in undef[:20]:
            print("   ", u)
    else:
        print(f"OK (nomes indefinidos: 0; avisos menores: {minor})")

    if run_tests:
        print("[3/3] pytest...", end=" ", flush=True)
        rc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=ROOT).returncode
        if rc != 0:
            ok = False
            print("FALHOU")
        else:
            print("OK")
    else:
        print("[3/3] pytest: pulado (--no-tests)")

    print("\n" + ("== TUDO OK ==" if ok else "== HA FALHAS =="))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
