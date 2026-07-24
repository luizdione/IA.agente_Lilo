#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emf_convert.py — Converte as figuras EMF extraídas de um .pzf para PNG/SVG/PDF.

Estratégia por plataforma (tenta em ordem, usa a 1ª que funciona):
  Windows  -> GDI+ nativo (System.Drawing via PowerShell): PNG sem instalar NADA.
  Qualquer -> Inkscape (png/svg/pdf), LibreOffice (png/pdf), ImageMagick (png).

PNG no Windows é o caminho garantido (o EMF é formato nativo do SO).
Para SVG/PDF vetorial, instale o Inkscape (melhor fidelidade) ou LibreOffice.

Uso:
  python emf_convert.py CAMINHO [--format png|svg|pdf] [--dpi 300] [--scale 2] [--outdir DIR]

CAMINHO pode ser um arquivo .emf ou uma pasta (converte todos os .emf, incl. subpasta figuras/).
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _emf_files(path: Path):
    if path.is_file() and path.suffix.lower() == ".emf":
        return [path]
    files = sorted(path.rglob("*.emf"))
    return files


# ---------------------------------------------------------------- Windows GDI+

# Lê uma lista TSV (origem<TAB>destino, uma por linha) — sem paths embutidos no
# script, o que elimina qualquer problema de aspas/escape/vírgula do PowerShell.
_PS_TEMPLATE = r"""
Add-Type -AssemblyName System.Drawing
$dpi = {dpi}
$scale = {scale}
$ok = 0; $fail = 0
foreach ($line in [System.IO.File]::ReadAllLines('{listfile}')) {{
  if ([string]::IsNullOrWhiteSpace($line)) {{ continue }}
  $parts = $line -split "`t"
  $src = $parts[0]; $dst = $parts[1]
  try {{
    $img = [System.Drawing.Image]::FromFile($src)
    $w = [int][math]::Max(1, $img.Width * $scale)
    $h = [int][math]::Max(1, $img.Height * $scale)
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $bmp.SetResolution($dpi, $dpi)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::White)
    $g.SmoothingMode = 'AntiAlias'
    $g.InterpolationMode = 'HighQualityBicubic'
    $g.DrawImage($img, 0, 0, $w, $h)
    $bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose(); $img.Dispose()
    Write-Output ("OK`t" + $dst)
    $ok++
  }} catch {{
    Write-Output ("FAIL`t" + $src + "`t" + $_.Exception.Message)
    $fail++
  }}
}}
Write-Output ("SUMMARY`t$ok`t$fail")
"""


def _unique_dst(files, base: Path | None, outdir: Path, ext: str):
    """Mapeia cada EMF a um destino ÚNICO em outdir. Como rglob junta .emf de
    várias pastas de extração (todas com 'figura_01.emf'), o stem sozinho colide
    e uma figura sobrescreve a outra. Aqui desambigua-se pelo caminho relativo
    (prefixo da pasta de extração), garantindo 1 destino por origem."""
    outdir.mkdir(parents=True, exist_ok=True)
    pairs, used = [], {}
    for f in files:
        stem = f.stem
        if base is not None and f != base:
            try:
                rel = f.relative_to(base).with_suffix("")
                parts = [p for p in rel.parts if p.lower() != "figuras"]
                if len(parts) > 1:
                    stem = "__".join(parts)
            except ValueError:
                pass
        stem = stem.replace("/", "_").replace("\\", "_")
        cand, i = stem, 2
        while cand in used:                    # blindagem final contra colisão
            cand = f"{stem}_{i}"; i += 1
        used[cand] = True
        pairs.append((f, outdir / f"{cand}.{ext}"))
    return pairs


def convert_windows_gdi(pairs, dpi=300, scale=2):
    """Converte EMF->PNG usando GDI+ nativo do Windows. `pairs` = [(src, dst)]."""
    tsv_lines = [f"{src}\t{dst}" for src, dst in pairs]
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as lf:
        lf.write("\n".join(tsv_lines))
        list_path = lf.name
    ps = _PS_TEMPLATE.format(dpi=dpi, scale=scale, listfile=list_path.replace("'", "''"))
    # .ps1 com BOM (utf-8-sig): o Windows PowerShell 5.x decodifica scripts SEM BOM
    # como ANSI/cp1252, corrompendo caminhos com acento (ex. perfil "C:\Users\José").
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig") as tf:
        tf.write(ps)
        ps_path = tf.name
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path],
            capture_output=True, text=True, timeout=600)
        print(r.stdout, end="")
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
    finally:
        for p in (ps_path, list_path):
            try:
                Path(p).unlink()
            except OSError:
                pass
    return [dst for _, dst in pairs if dst.exists()]


# ---------------------------------------------------------------- fallbacks

def _run(cmd, timeout=300):
    """subprocess.run com timeout; retorna None em timeout (para pular o arquivo)."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT\t{cmd[0]}", file=sys.stderr)
        return None


def convert_inkscape(pairs, fmt="png", dpi=300):
    exe = shutil.which("inkscape")
    if not exe:
        return None
    out = []
    for src, dst in pairs:
        _run([exe, str(src), f"--export-filename={dst}", f"--export-dpi={dpi}"])  # Inkscape 1.x
        if not dst.exists():
            key = {"png": "--export-png", "pdf": "--export-pdf", "svg": "--export-plain-svg"}.get(fmt)
            if key:  # Inkscape 0.92
                _run([exe, str(src), key, str(dst), f"--export-dpi={dpi}"])
        if dst.exists():
            out.append(dst); print(f"OK\t{dst}")
    return out


def convert_libreoffice(pairs, fmt="png"):
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return None
    out = []
    for src, dst in pairs:
        # LibreOffice grava <stem>.<fmt> na outdir; convertemos 1 a 1 e renomeamos
        # para o destino único (evita colisão de stems iguais de pastas diferentes).
        _run([exe, "--headless", "--convert-to", fmt, "--outdir", str(dst.parent), str(src)])
        lo_out = dst.parent / (src.stem + "." + fmt)
        if lo_out.exists() and lo_out != dst:
            try:
                lo_out.replace(dst)
            except OSError:
                pass
        if dst.exists():
            out.append(dst); print(f"OK\t{dst}")
    return out


def convert_imagemagick(pairs, fmt="png", dpi=300):
    exe = shutil.which("magick")
    if not exe:
        return None
    out = []
    for src, dst in pairs:
        _run([exe, "-density", str(dpi), str(src), str(dst)])
        if dst.exists():
            out.append(dst); print(f"OK\t{dst}")
    return out


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Converte figuras EMF do Prism para PNG/SVG/PDF.")
    ap.add_argument("caminho", help="arquivo .emf ou pasta (rglob *.emf)")
    ap.add_argument("--format", default="png", choices=["png", "svg", "pdf"])
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--scale", type=int, default=2, help="fator de escala (só GDI+/PNG)")
    ap.add_argument("--outdir", default=None, help="pasta de saída (default: <pasta>/<fmt>)")
    a = ap.parse_args(argv)

    path = Path(a.caminho)
    files = _emf_files(path)
    if not files:
        print("Nenhum .emf encontrado em:", path, file=sys.stderr)
        return 1
    base = None if path.is_file() else path
    outdir = Path(a.outdir) if a.outdir else (path.parent if path.is_file() else path) / a.format
    pairs = _unique_dst(files, base, outdir, a.format)
    print(f"[emf_convert] {len(files)} arquivo(s) EMF → {a.format.upper()} em {outdir}", file=sys.stderr)

    made = None
    if a.format == "png" and sys.platform == "win32":
        try:
            made = convert_windows_gdi(pairs, dpi=a.dpi, scale=a.scale)
        except subprocess.TimeoutExpired:
            print("GDI+ excedeu o tempo; tentando fallbacks.", file=sys.stderr)
            made = None
    if not made:
        for fn in (convert_inkscape, convert_libreoffice, convert_imagemagick):
            made = fn(pairs, fmt=a.format, dpi=a.dpi) if fn in (convert_inkscape, convert_imagemagick) \
                else fn(pairs, fmt=a.format)
            if made:
                break
    if not made:
        print("\nNenhum conversor funcionou.", file=sys.stderr)
        if a.format == "png":
            print("No Windows o GDI+ deveria bastar. Fora do Windows, instale Inkscape/LibreOffice/ImageMagick.",
                  file=sys.stderr)
        else:
            print(f"Para {a.format.upper()} vetorial instale o Inkscape (recomendado) ou LibreOffice.",
                  file=sys.stderr)
        return 2
    n_unicos = len(set(made))
    print(f"[emf_convert] {n_unicos} arquivo(s) gerado(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
