#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
perfil.py — Perfila e consulta arquivos de dados grandes SEM despejá-los no
contexto. Em vez de ler uma planilha de milhões de linhas ou um .npz de GB, o
modelo lê um PERFIL compacto (forma, colunas, estatísticas, amostra) e faz
CONSULTAS dirigidas que devolvem só as linhas/valores pedidos.

Formatos: .csv/.tsv/.txt, .xlsx/.xls, .json, .npz/.npy, .parquet, .cif/.pdb,
.fasta/.fa/.fna. (Para GraphPad .pzf/.pzfx use a skill graphpad_prism; para
SnapGene .dna use scripts/snapgene.py.)

Comandos:
  perfil    ARQ [--n 5] [--sheet NOME]                     # perfil compacto
  consultar ARQ.csv [--query "expr"] [--cols a,b] [--head N] [--describe COL]
  cabeca    ARQ [--n 20]                                    # só as primeiras linhas

Requer: pandas, numpy (openpyxl p/ xlsx; pyarrow/fastparquet p/ parquet).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def _out_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def _sep_for(path: Path):
    if path.suffix.lower() == ".tsv":
        return "\t"
    try:
        head = path.open("r", encoding="utf-8", errors="replace").readline()
    except OSError:
        return ","
    counts = {",": head.count(","), ";": head.count(";"), "\t": head.count("\t"), "|": head.count("|")}
    return max(counts, key=counts.get) or ","


# ------------------------------------------------------------- perfil por tipo

def profile_table(df, path: Path, n=5, sheet=None):
    import pandas as pd  # noqa
    L = [f"# Perfil — `{path.name}`" + (f" (aba: {sheet})" if sheet else ""), "",
         f"- **Forma:** {df.shape[0]} linhas × {df.shape[1]} colunas · {round(path.stat().st_size/1e6,2)} MB",
         "", "## Colunas", "| Coluna | Tipo | Nulos | Resumo |", "|---|---|--:|---|"]
    MAX_COLS = 60  # matrizes ômicas têm milhares de colunas: nunca listar todas
    for c in list(df.columns)[:MAX_COLS]:
        s = df[c]
        nulls = int(s.isna().sum())
        dt = str(s.dtype)
        try:
            if s.dtype.kind in "biufc":
                d = s.describe()
                resumo = f"min={d.get('min'):.4g} · méd={d.get('mean'):.4g} · máx={d.get('max'):.4g}"
            else:
                nun = s.nunique(dropna=True)
                top = s.dropna().astype(str).value_counts().head(3)
                # trunca cada valor: colunas de texto longo (ex.: sequências de DNA)
                # não podem explodir o perfil — o objetivo é economia de tokens.
                resumo = f"{nun} únicos · top: " + ", ".join(
                    f"{k[:40].replace(chr(10),' ')}{'…' if len(k) > 40 else ''}({v})" for k, v in top.items())
        except Exception:
            resumo = ""
        L.append(f"| {c} | {dt} | {nulls} | {resumo} |")
    if df.shape[1] > MAX_COLS:
        L.append(f"| … +{df.shape[1] - MAX_COLS} colunas omitidas | | | |")
    L += ["", f"## Amostra (primeiras {n} linhas)", "```",
          df.head(n).to_string(max_cols=40, max_colwidth=30), "```"]
    return "\n".join(L)


def profile_csv(path, n, **kw):
    import pandas as pd
    sep = _sep_for(path)
    df = pd.read_csv(path, sep=sep, engine="c", low_memory=False, on_bad_lines="skip")
    return profile_table(df, path, n)


def profile_xlsx(path, n, sheet=None, **kw):
    import pandas as pd
    xl = pd.ExcelFile(path)
    if sheet is None and len(xl.sheet_names) > 1:
        L = [f"# Perfil — `{path.name}` · {len(xl.sheet_names)} abas", ""]
        for sh in xl.sheet_names:
            d = xl.parse(sh, nrows=0)
            full = xl.parse(sh)
            L.append(f"- **{sh}**: {full.shape[0]}×{full.shape[1]} — cols: "
                     + ", ".join(map(str, list(d.columns)[:12])))
        L.append("\nUse `--sheet NOME` para o perfil completo de uma aba.")
        return "\n".join(L)
    sh = sheet or xl.sheet_names[0]
    return profile_table(xl.parse(sh), path, n, sheet=sh)


def profile_json(path, n, **kw):
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))

    MAX_DEPTH, budget = 6, [3000]  # teto de profundidade e de linhas: JSON amplo
    # e profundo cresce ~20^nível; sem teto isso explodiria o contexto.

    def describe(v, depth=0, key=""):
        pad = "  " * depth
        if budget[0] <= 0:
            return []
        budget[0] -= 1
        if depth >= MAX_DEPTH:
            return [f"{pad}{key}… (truncado por profundidade)"]
        if isinstance(v, dict):
            out = [f"{pad}{key}{{}} ({len(v)} chaves)"]
            for k in list(v.keys())[:20]:
                if budget[0] <= 0:
                    out.append(f"{pad}  … (perfil truncado)"); break
                out += describe(v[k], depth + 1, str(k) + ": ")
            if len(v) > 20:
                out.append(f"{pad}  … +{len(v)-20} chaves")
            return out
        if isinstance(v, list):
            head = [f"{pad}{key}[] ({len(v)} itens)"]
            if v:
                head += describe(v[0], depth + 1, "[0] ")
            return head
        s = repr(v)
        return [f"{pad}{key}{type(v).__name__} = {s[:60]}"]

    L = [f"# Perfil JSON — `{path.name}` ({round(path.stat().st_size/1e6,2)} MB)", "", "```"]
    L += describe(data)
    L.append("```")
    return "\n".join(L)


def profile_npz(path, n, **kw):
    # Lê APENAS o cabeçalho de cada array (shape/dtype) — nunca materializa os
    # dados na RAM. Um .npy/.npz de vários GB é justamente o caso que a skill
    # existe para resolver; np.load sem mmap causaria OOM.
    import numpy as np
    from numpy.lib import format as npf
    import zipfile
    L = [f"# Perfil NumPy — `{path.name}` ({round(path.stat().st_size/1e6,2)} MB)", ""]
    if path.suffix.lower() == ".npy":
        try:
            arr = np.load(path, mmap_mode="r")  # mmap: shape/dtype sem carregar dados
            L.append(f"- array único: shape={arr.shape} dtype={arr.dtype}")
        except (ValueError, OSError):            # object/pickle não é mmap-ável: lê só o header
            with open(path, "rb") as f:
                ver = npf.read_magic(f)
                shape, _fortran, dtype = npf._read_array_header(f, ver)
            L.append(f"- array único (object/pickle): shape={shape} dtype={dtype}")
        return "\n".join(L)
    with zipfile.ZipFile(path) as zf:            # .npz é um zip de membros .npy
        members = [nm for nm in zf.namelist() if nm.endswith(".npy")]
        L.append(f"{len(members)} array(s):")
        L += ["| Nome | Shape | Dtype |", "|---|---|---|"]
        for nm in members:
            try:
                with zf.open(nm) as f:           # lê só o header (descompressão incremental)
                    ver = npf.read_magic(f)
                    shape, _fortran, dtype = npf._read_array_header(f, ver)
                L.append(f"| {nm[:-4]} | {shape} | {dtype} |")
            except Exception:
                L.append(f"| {nm[:-4]} | ? | ? |")
    return "\n".join(L)


def profile_parquet(path, n, **kw):
    import pandas as pd
    return profile_table(pd.read_parquet(path), path, n)


def profile_structure(path, n, **kw):
    """Metadados leves de .pdb/.cif (sem despejar coordenadas)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    suf = path.suffix.lower()
    L = [f"# Perfil estrutura — `{path.name}` ({round(path.stat().st_size/1e6,2)} MB)", ""]
    if suf == ".pdb":
        atoms = sum(1 for l in lines if l.startswith(("ATOM", "HETATM")))
        chains = sorted({l[21] for l in lines if l.startswith("ATOM") and len(l) > 21})
        title = " ".join(l[10:].strip() for l in lines if l.startswith("TITLE"))
        models = sum(1 for l in lines if l.startswith("MODEL"))
        reso = next((l.split("RESOLUTION.")[1].strip() for l in lines
                     if l.startswith("REMARK   2") and "RESOLUTION." in l), "")
        L += [f"- Título: {title[:200]}", f"- Átomos: {atoms} · cadeias: {','.join(chains)} "
              f"· modelos: {models or 1}" + (f" · resolução: {reso}" if reso else "")]
    else:  # .cif / .mmcif
        title = next((l.split("'")[1] for l in lines if l.strip().startswith("_struct.title") and "'" in l), "")
        atoms = sum(1 for l in lines if l.startswith(("ATOM ", "HETATM")))
        L += [f"- Título: {title[:200]}", f"- Linhas de átomo (_atom_site): {atoms}"]
    return "\n".join(L)


def profile_fasta(path, n, **kw):
    # cur=None = "ainda não vi um cabeçalho"; assim uma sequência de comprimento 0
    # (dois '>' seguidos) entra em lengths e len(lengths)==seqs, e um arquivo sem
    # nenhum '>' não gera estatística fantasma de comprimento.
    seqs, cur, lengths, names = 0, None, [], []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                if cur is not None:
                    lengths.append(cur)
                cur = 0; seqs += 1
                if len(names) < 10:
                    names.append(line[1:].strip()[:60])
            elif cur is not None:
                cur += len(line.strip())
    if cur is not None:
        lengths.append(cur)
    L = [f"# Perfil FASTA — `{path.name}` ({round(path.stat().st_size/1e6,2)} MB)", "",
         f"- **{seqs} sequência(s)**"]
    if lengths:
        L.append(f"- comprimento: min={min(lengths)} · méd={sum(lengths)//len(lengths)} · máx={max(lengths)} pb")
    L.append("- primeiras: " + "; ".join(names[:5]))
    return "\n".join(L)


_DISPATCH = {
    ".csv": profile_csv, ".tsv": profile_csv, ".txt": profile_csv,
    ".xlsx": profile_xlsx, ".xls": profile_xlsx,
    ".json": profile_json,
    ".npz": profile_npz, ".npy": profile_npz,
    ".parquet": profile_parquet, ".pq": profile_parquet,
    ".pdb": profile_structure, ".cif": profile_structure, ".mmcif": profile_structure,
    ".fasta": profile_fasta, ".fa": profile_fasta, ".fna": profile_fasta,
}


# ------------------------------------------------------------- consultar

def cmd_consultar(args):
    import pandas as pd
    path = Path(args.arquivo)
    sep = _sep_for(path) if path.suffix.lower() in (".csv", ".tsv", ".txt") else None
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=args.sheet or 0)
    elif path.suffix.lower() in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, sep=sep, low_memory=False, on_bad_lines="skip")
    if args.query:
        try:
            df = df.query(args.query)
        except Exception as e:
            print(f"[erro na query: {e}]", file=sys.stderr); return 2
    if args.cols:
        cols = [c.strip() for c in args.cols.split(",")]
        df = df[[c for c in cols if c in df.columns]]
    if args.describe:
        if args.describe not in df.columns:
            print(f"[coluna não encontrada: {args.describe}. Disponíveis: "
                  f"{', '.join(map(str, list(df.columns)[:50]))}]", file=sys.stderr)
            return 2
        print(df[args.describe].describe().to_string()); return 0
    out = df.head(args.head)
    print(f"[{len(df)} linha(s) após filtro; mostrando {min(args.head, len(df))}]")
    print(out.to_string(max_cols=40, max_colwidth=40))
    return 0


def cmd_cabeca(args):
    import pandas as pd
    path = Path(args.arquivo)
    sep = _sep_for(path) if path.suffix.lower() in (".csv", ".tsv", ".txt") else ","
    df = pd.read_csv(path, sep=sep, nrows=args.n, low_memory=False, on_bad_lines="skip")
    print(df.to_string(max_cols=40, max_colwidth=40))
    return 0


def cmd_perfil(args):
    path = Path(args.arquivo)
    fn = _DISPATCH.get(path.suffix.lower())
    if not fn:
        print(f"[tipo não suportado: {path.suffix}. Suportados: {', '.join(sorted(_DISPATCH))}. "
              "Para .pzf/.pzfx use graphpad_prism; para .dna use snapgene.py.]", file=sys.stderr)
        return 2
    try:
        print(fn(path, n=args.n, sheet=args.sheet))
    except Exception as e:
        print(f"[erro ao perfilar {path.name}: {e}]", file=sys.stderr); return 1
    return 0


def main(argv=None):
    _out_utf8()
    ap = argparse.ArgumentParser(description="Perfila e consulta dados grandes sem despejá-los (economia de tokens).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("perfil", help="perfil compacto de um arquivo de dados")
    s.add_argument("arquivo"); s.add_argument("--n", type=int, default=5)
    s.add_argument("--sheet", help="aba (xlsx)"); s.set_defaults(func=cmd_perfil)

    s = sub.add_parser("consultar", help="consulta dirigida (filtra/seleciona/descreve)")
    s.add_argument("arquivo"); s.add_argument("--query"); s.add_argument("--cols")
    s.add_argument("--head", type=int, default=20); s.add_argument("--describe")
    s.add_argument("--sheet"); s.set_defaults(func=cmd_consultar)

    s = sub.add_parser("cabeca", help="primeiras N linhas de uma tabela")
    s.add_argument("arquivo"); s.add_argument("--n", type=int, default=20)
    s.set_defaults(func=cmd_cabeca)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
