"""Arquivos de texto/codigo do host (grupo codigo): ler numerado, escrever, editar com diff,
buscar (grep) e listar (glob).

Pensado para um modelo local de ~30B usar bem: poucos parametros planos com default, erros
que ensinam a proxima chamada ("antigo aparece 3 vezes (linhas ...)"), diff unificado em toda
alteracao e tolerancia a CRLF. Escrita, edicao e cwd so dentro de `comum.RAIZES`
(LILO_HOST_RAIZES); segredos (`comum.caminho_protegido`) nunca passam por aqui.
"""
from __future__ import annotations

import difflib
import fnmatch
import os
import re
from pathlib import Path

from . import comum
from .comum import erro, resolver
from .pastas import BUSCA_MAX_BYTES, IGNORAR, TEXTO_EXT
from .resumir import EXT_BINARIAS, _parece_binario

LER_MAX_BYTES = 2_000_000
LER_MAX_LINHAS = 400
LER_MAX_CHARS = 16000
LINHA_MAX = 1000
ESCREVER_MAX = 200_000
ANTIGO_MAX = 20_000
NOVO_MAX = 50_000
DIFF_MAX_LINHAS = 80
BUSCA_MAX = 200
LISTAR_MAX = 1000


# ------------------------------------------------------------------ apoio
def _ler_texto(p: Path) -> tuple[str, str] | str:
    """(texto, fim_de_linha) ou [ERRO]. Decodifica utf-8 e cai para latin-1."""
    if p.suffix.lower() in EXT_BINARIAS:
        return erro("arquivo binario (%s): use ler_pdf/ler_texto para PDF e DOCX" % p.suffix)
    try:
        if p.stat().st_size > LER_MAX_BYTES:
            return erro("arquivo acima de %d bytes; use pasta_buscar ou leia por partes com outro meio"
                        % LER_MAX_BYTES)
        raw = p.read_bytes()
    except OSError as e:
        return erro("nao consegui ler %s: %s" % (p, e))
    if _parece_binario(raw):
        return erro("arquivo parece binario: %s" % p)
    try:
        texto = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = raw.decode("latin-1")
    return texto, ("\r\n" if "\r\n" in texto else "\n")


def _guarda_escrita(p: Path) -> str | None:
    if comum.caminho_protegido(p, escrita=True):
        return erro("caminho protegido (segredo ou .git): %s" % p)
    if not comum.dentro_das_raizes(p):
        return erro("fora das raizes permitidas para escrita (%s): %s"
                    % ("; ".join(str(r) for r in comum.RAIZES), p))
    return None


def _gravar(p: Path, texto: str, fim: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    normal = texto.replace("\r\n", "\n")
    with p.open("w", encoding="utf-8", newline="") as fh:
        fh.write(normal.replace("\n", fim) if fim != "\n" else normal)


def _aviso_sintaxe(p: Path, texto: str) -> str:
    if p.suffix.lower() != ".py":
        return ""
    try:
        compile(texto, str(p), "exec")
    except SyntaxError as e:
        return "\n[aviso] sintaxe Python: linha %s: %s" % (e.lineno, e.msg)
    return ""


def _numero_linhas(texto: str) -> int:
    return len(texto.splitlines())


def _ignorado(partes: tuple[str, ...]) -> bool:
    return any(x in IGNORAR or (x.startswith(".") and x not in (".", "..")) for x in partes)


# ------------------------------------------------------------------- tools
def ler(caminho: str, inicio: int = 1, linhas: int = 200) -> str:
    """Texto com linhas numeradas (`N<TAB>texto`), ate 400 linhas / 16k caracteres por chamada."""
    p = resolver(caminho)
    if not p.is_file():
        return erro("arquivo nao existe: %s" % p)
    if comum.caminho_protegido(p, escrita=False):
        return erro("caminho protegido (segredo): %s" % p)
    r = _ler_texto(p)
    if isinstance(r, str):
        return r
    texto, _ = r
    todas = texto.splitlines()
    total = len(todas)
    inicio = max(1, int(inicio or 1))
    linhas = max(1, min(LER_MAX_LINHAS, int(linhas or 200)))
    if inicio > total:
        return erro("inicio=%d alem do fim (%d linhas)" % (inicio, total))
    saida: list[str] = []
    chars = 0
    fim = inicio - 1
    for n in range(inicio, min(total, inicio + linhas - 1) + 1):
        l = todas[n - 1]
        if len(l) > LINHA_MAX:
            l = l[:LINHA_MAX] + " ...[linha cortada]"
        if chars + len(l) > LER_MAX_CHARS and saida:
            break
        saida.append("%d\t%s" % (n, l))
        chars += len(l) + 1
        fim = n
    cab = "[ok] %s: linhas %d-%d de %d" % (p, inicio, fim, total)
    if fim < total:
        cab += "; para continuar: inicio=%d" % (fim + 1)
    return cab + "\n" + "\n".join(saida)


def escrever(caminho: str, conteudo: str, sobrescrever: bool = False) -> str:
    """Cria um arquivo UTF-8 (e as pastas). Existente so com sobrescrever=True; devolve o diff."""
    p = resolver(caminho)
    g = _guarda_escrita(p)
    if g:
        return g
    if len(conteudo) > ESCREVER_MAX:
        return erro("conteudo acima de %d caracteres; grave em partes com arquivo_editar" % ESCREVER_MAX)
    if p.is_dir():
        return erro("e uma pasta: %s" % p)
    diff = ""
    fim = "\n"
    if p.exists():
        r = _ler_texto(p)
        if isinstance(r, str):
            return r
        antigo, fim = r
        if not sobrescrever:
            return erro("ja existe (%d linhas): use arquivo_editar para alterar um trecho ou "
                        "sobrescrever=true para trocar tudo" % _numero_linhas(antigo))
        diff = "\n" + comum.diff_unificado(antigo, conteudo, p.name, DIFF_MAX_LINHAS)
    try:
        _gravar(p, conteudo, fim)
    except OSError as e:
        return erro("nao consegui gravar %s: %s" % (p, e))
    return ("[ok] gravado %s (%d linhas, %d bytes)" % (p, _numero_linhas(conteudo), p.stat().st_size)
            + diff + _aviso_sintaxe(p, conteudo))


def _dica(texto: str, antigo: str) -> str:
    """Linhas do arquivo parecidas com a 1a linha nao vazia de `antigo`."""
    alvo = next((x.strip() for x in antigo.splitlines() if x.strip()), "")
    if not alvo:
        return ""
    linhas = texto.splitlines()
    parecidas = difflib.get_close_matches(alvo, [x.strip() for x in linhas], n=3, cutoff=0.6)
    achados = []
    for par in parecidas:
        for n, x in enumerate(linhas, 1):
            if x.strip() == par:
                achados.append("%d: %s" % (n, x.strip()[:120]))
                break
    return ("; linhas parecidas: " + " | ".join(achados)) if achados else ""


def editar(caminho: str, antigo: str, novo: str, todas: bool = False) -> str:
    """Troca o trecho EXATO `antigo` por `novo` (unico, salvo todas=True); devolve o diff."""
    p = resolver(caminho)
    g = _guarda_escrita(p)
    if g:
        return g
    if not p.is_file():
        return erro("arquivo nao existe: %s (para criar use arquivo_escrever)" % p)
    if not antigo:
        return erro("`antigo` vazio: informe o trecho exato a trocar (2-3 linhas de contexto)")
    if len(antigo) > ANTIGO_MAX or len(novo) > NOVO_MAX:
        return erro("trecho grande demais (antigo ate %d, novo ate %d caracteres)" % (ANTIGO_MAX, NOVO_MAX))
    r = _ler_texto(p)
    if isinstance(r, str):
        return r
    texto, fim = r
    t = texto.replace("\r\n", "\n")
    a = antigo.replace("\r\n", "\n")
    n = novo.replace("\r\n", "\n")
    if a == n:
        return erro("`antigo` e `novo` sao iguais: nada a fazer")
    vezes = t.count(a)
    if vezes == 0:
        return erro("`antigo` nao encontrado em %s%s" % (p.name, _dica(t, a)))
    if vezes > 1 and not todas:
        pos, achados = 0, []
        while True:
            i = t.find(a, pos)
            if i < 0:
                break
            achados.append(str(t.count("\n", 0, i) + 1))
            pos = i + 1
        return erro("`antigo` aparece %d vezes (linhas %s): inclua mais contexto para ser unico "
                    "ou use todas=true" % (vezes, ", ".join(achados)))
    novo_texto = t.replace(a, n) if todas else t.replace(a, n, 1)
    try:
        _gravar(p, novo_texto, fim)
    except OSError as e:
        return erro("nao consegui gravar %s: %s" % (p, e))
    return ("[ok] %s: %d substituicao(oes)\n" % (p, vezes if todas else 1)
            + comum.diff_unificado(t, novo_texto, p.name, DIFF_MAX_LINHAS) + _aviso_sintaxe(p, novo_texto))


def buscar(padrao: str, caminho: str = ".", glob: str = "", regex: bool = False,
           contexto: int = 0, max_resultados: int = 40) -> str:
    """Procura `padrao` nos arquivos de texto (como grep -rn): `arquivo:linha: texto`."""
    if not (padrao or "").strip():
        return erro("padrao vazio")
    p = resolver(caminho)
    if not p.exists():
        return erro("caminho nao existe: %s" % p)
    try:
        rx = re.compile(padrao if regex else re.escape(padrao), re.IGNORECASE)
    except re.error as e:
        return erro("expressao regular invalida: %s" % e)
    max_resultados = max(1, min(BUSCA_MAX, int(max_resultados or 40)))
    contexto = max(0, min(5, int(contexto or 0)))
    arquivos: list[Path]
    if p.is_file():
        arquivos = [p]
    else:
        arquivos = []
        for raiz, dirs, nomes in os.walk(p):
            dirs[:] = sorted(d for d in dirs if d not in IGNORAR and not d.startswith("."))
            for nome in sorted(nomes):
                f = Path(raiz) / nome
                if f.suffix.lower() in EXT_BINARIAS:
                    continue
                if glob:
                    rel = str(f.relative_to(p)).replace("\\", "/")
                    if not (fnmatch.fnmatch(nome, glob) or fnmatch.fnmatch(rel, glob)):
                        continue
                elif f.suffix.lower() not in TEXTO_EXT:
                    continue
                arquivos.append(f)
    hits: list[str] = []
    n = 0
    cortado = False
    for f in arquivos:
        try:
            if f.stat().st_size > BUSCA_MAX_BYTES:
                continue
            linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(f.relative_to(p)) if p.is_dir() else f.name
        for i, linha in enumerate(linhas):
            if not rx.search(linha):
                continue
            if n >= max_resultados:
                cortado = True
                break
            n += 1
            for j in range(max(0, i - contexto), i):
                hits.append("%s-%d- %s" % (rel, j + 1, linhas[j].strip()[:200]))
            hits.append("%s:%d: %s" % (rel, i + 1, linha.strip()[:200]))
            for j in range(i + 1, min(len(linhas), i + 1 + contexto)):
                hits.append("%s-%d- %s" % (rel, j + 1, linhas[j].strip()[:200]))
        if cortado:
            break
    if not hits:
        return "[ok] nenhum resultado para %r em %s%s" % (
            padrao, p, "" if regex else " (busca literal; regex=true para expressoes)")
    cab = "[ok] %d resultado(s) para %r em %s" % (n, padrao, p)
    if cortado:
        cab += "; cortado em %d: refine o padrao ou use glob" % max_resultados
    return cab + "\n" + "\n".join(hits)


def listar(padrao: str = "**/*", caminho: str = ".", max_resultados: int = 200) -> str:
    """Arquivos por glob (`**/*.py`), caminho relativo e tamanho; ignora .git e afins."""
    p = resolver(caminho)
    if not p.is_dir():
        return erro("pasta nao existe: %s" % p)
    max_resultados = max(1, min(LISTAR_MAX, int(max_resultados or 200)))
    saida: list[str] = []
    cortado = False
    try:
        for f in sorted(p.glob(padrao or "**/*")):
            rel = f.relative_to(p)
            if _ignorado(rel.parts) or not f.is_file():
                continue
            if len(saida) >= max_resultados:
                cortado = True
                break
            try:
                t = f.stat().st_size
            except OSError:
                t = 0
            saida.append("%s  (%d B)" % (str(rel).replace("\\", "/"), t))
    except (OSError, ValueError) as e:
        return erro("glob invalido ou pasta inacessivel: %s" % e)
    cab = "[ok] %d arquivo(s) para %r em %s" % (len(saida), padrao, p)
    if cortado:
        cab += "; lista cortada em %d" % max_resultados
    return cab + ("\n" + "\n".join(saida) if saida else "")
