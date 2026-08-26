"""Tools do LILO v13 — 6 ferramentas + `executar_tool`, o CHOKE-POINT unico.

Regra nao-negociavel (CLAUDE.md): SO `executar_tool` executa. As
implementacoes (_ler, _escrever, ...) sao privadas e nada fora deste modulo
as chama — correcao do buraco do composed.py do legado, que escrevia e
executava sem passar pelo portao.

Herdado do v12.15-legado: escrita atomica (tmp+fsync+os.replace), deny-list
de comandos perigosos, padroes de git write (never-commit-unless-asked),
allow-list por caminho resolvido e o formato [exit=N] do shell. Novidades:
`editar` (replace de trecho unico), `buscar` com ignore-list (o fs_search
antigo lia .git e node_modules inteiros) e kill da ARVORE de processos no
timeout do shell (o legado matava so o shell pai).
"""
from __future__ import annotations

import difflib
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Callable

from lilo import config, memoria, mcp_cliente, portao
from lilo.log import get_logger

log = get_logger("tools")

# --- limites ----------------------------------------------------------------
LIMITE_RESULTADO = 30_000       # teto global por resultado de tool (chars)
LER_MAX_LINHAS = 2_000
LER_MAX_BYTES = 50_000
LISTAR_MAX = 200
BUSCAR_MAX_HITS = 50
BUSCAR_MAX_ARQ = 1_000_000      # pula arquivos > 1 MB
SHELL_STDOUT_MAX = 8_000
SHELL_STDERR_MAX = 2_000

# Diretorios-lixo (heranca do dir_synthesis do legado + extras)
_SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".idea", ".vscode", "dist", "build", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "site-packages", ".tox", ".eggs",
    "htmlcov", ".ipynb_checkpoints",
}

# Comandos destrutivos: NUNCA executam, em nenhum modo (heranca desktop/agent.py)
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/(?:\s|$)", r"rm\s+-rf\s+~", r"format\s+[a-z]:",
    r"del\s+/[fsq]\s+", r":\(\)\{.*\};:", r"\bmkfs\b",
    r"\bdd\b.*\bof=/dev/", r">\s*/dev/sd[a-z]", r"\bshutdown\b", r"\breboot\b",
]

# Escrita em git: kind git_write (sensivel ate em auto)
GIT_WRITE_PATTERNS = [
    r"\bgit\s+(commit|push)\b", r"\bgit\b.*\s--force\b",
    r"\bgit\s+reset\s+--hard\b", r"\bgit\s+clean\b.*\s-\w*f",
]


def _cmd_perigoso(cmd: str) -> bool:
    return any(re.search(p, cmd, re.IGNORECASE) for p in DANGEROUS_PATTERNS)


def _cmd_git_write(cmd: str) -> bool:
    return any(re.search(p, cmd, re.IGNORECASE) for p in GIT_WRITE_PATTERNS)


# --- allow-list -------------------------------------------------------------
def _resolver(caminho: str) -> Path:
    return Path(caminho).expanduser().resolve()


def _dentro_allow(p: Path) -> bool:
    for raiz in config.allow_list():
        try:
            p.relative_to(raiz)
            return True
        except ValueError:
            continue
    return False


def _kind_escrita(p: Path) -> str:
    return "write" if _dentro_allow(p) else "write_outside"


def _parece_binario(p: Path) -> bool:
    try:
        return b"\x00" in p.open("rb").read(1024)
    except OSError:
        return False


def _ler_texto(p: Path, max_bytes: int = LER_MAX_BYTES) -> str:
    bruto = p.open("rb").read(max_bytes)
    try:
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        return bruto.decode("latin-1", errors="replace")


# --- implementacoes PRIVADAS ------------------------------------------------
def _ler(args: dict) -> str:
    p = _resolver(args["caminho"])
    if not p.exists():
        return "[ERRO] arquivo nao existe: %s" % p
    if p.is_dir():
        return "[ERRO] %s e um diretorio — use a tool listar" % p
    if _parece_binario(p):
        return "[ERRO] arquivo binario (%d bytes) — nao ha texto para ler" % (
            p.stat().st_size)
    offset = max(1, int(args.get("offset") or 1))
    limite = min(LER_MAX_LINHAS, int(args.get("limite") or LER_MAX_LINHAS))
    linhas = _ler_texto(p).splitlines()
    fatia = linhas[offset - 1: offset - 1 + limite]
    corpo = "\n".join("%d→%s" % (offset + i, ln) for i, ln in enumerate(fatia))
    resto = len(linhas) - (offset - 1 + len(fatia))
    if resto > 0:
        corpo += "\n... (+%d linhas — use offset=%d)" % (resto, offset + len(fatia))
    return corpo or "(arquivo vazio)"


def _escrever(args: dict) -> str:
    """Escrita ATOMICA (heranca fs_write do legado): tmp + flush + fsync +
    os.replace — queda de energia no meio nao corrompe o arquivo destino."""
    p = _resolver(args["caminho"])
    conteudo = str(args["conteudo"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".lilo_tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            f.write(conteudo)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if tmp.exists():  # tmp orfao de uma falha anterior
            try:
                tmp.unlink()
            except OSError:
                pass
    return "[OK] escrito %s (%d chars)" % (p, len(conteudo))


def _editar(args: dict) -> str:
    p = _resolver(args["caminho"])
    if not p.exists():
        return "[ERRO] arquivo nao existe: %s" % p
    antigo, novo = str(args["texto_antigo"]), str(args["texto_novo"])
    if antigo == novo:
        return "[ERRO] texto_antigo e texto_novo sao iguais"
    texto = _ler_texto(p, max_bytes=5_000_000)
    n = texto.count(antigo)
    if n == 0:
        return "[ERRO] texto_antigo nao encontrado em %s — leia o arquivo e copie o trecho EXATO" % p.name
    todas = bool(args.get("todas"))
    if n > 1 and not todas:
        return "[ERRO] texto_antigo nao e unico (%d ocorrencias) — inclua mais contexto ou use todas=true" % n
    resultado = texto.replace(antigo, novo) if todas else texto.replace(antigo, novo, 1)
    _escrever({"caminho": str(p), "conteudo": resultado})
    return "[OK] editado %s (%d substituicao%s)" % (p, n if todas else 1,
                                                    "oes" if (n if todas else 1) > 1 else "")


def _listar(args: dict) -> str:
    p = _resolver(args.get("caminho") or ".")
    if not p.is_dir():
        return "[ERRO] diretorio nao existe: %s" % p
    padrao = args.get("padrao") or "*"
    it = p.rglob(padrao) if args.get("recursivo") else p.glob(padrao)
    saida, n = [], 0
    for item in sorted(it):
        if any(parte in _SKIP_DIRS for parte in item.parts):
            continue
        saida.append(str(item.relative_to(p)) + ("/" if item.is_dir() else ""))
        n += 1
        if n >= LISTAR_MAX:
            saida.append("... (+%d, refine o padrao)" % LISTAR_MAX)
            break
    return "\n".join(saida) or "(vazio)"


def _buscar(args: dict) -> str:
    """grep com juizo: usa rg se existir; senao puro-Python com ignore-list e
    skip de binarios (o fs_search do legado lia .git/node_modules inteiros)."""
    padrao = str(args["padrao"])
    raiz = _resolver(args.get("raiz") or ".")
    if not raiz.is_dir():
        return "[ERRO] raiz nao existe: %s" % raiz
    glob_arq = args.get("glob_arquivos") or ""
    usar_regex = bool(args.get("regex"))

    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "--no-heading", "-n", "-m", str(BUSCAR_MAX_HITS)]
        if not usar_regex:
            cmd.append("-F")
        if glob_arq:
            cmd += ["-g", glob_arq]
        cmd += [padrao, str(raiz)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                               encoding="utf-8", errors="replace")
            if r.returncode in (0, 1):  # 1 = sem match
                return r.stdout.strip()[:LIMITE_RESULTADO] or "(nenhum resultado)"
        except (subprocess.TimeoutExpired, OSError):
            pass  # cai no python puro

    rx = re.compile(padrao if usar_regex else re.escape(padrao))
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for nome in filenames:
            arq = Path(dirpath) / nome
            if glob_arq and not arq.match(glob_arq):
                continue
            try:
                if arq.stat().st_size > BUSCAR_MAX_ARQ or _parece_binario(arq):
                    continue
                for i, ln in enumerate(_ler_texto(arq, BUSCAR_MAX_ARQ).splitlines(), 1):
                    if rx.search(ln):
                        hits.append("%s:%d: %s" % (arq.relative_to(raiz), i,
                                                   ln.strip()[:200]))
                        if len(hits) >= BUSCAR_MAX_HITS:
                            hits.append("... (teto de %d hits)" % BUSCAR_MAX_HITS)
                            return "\n".join(hits)
            except OSError:
                continue
    return "\n".join(hits) or "(nenhum resultado)"


def _shell(args: dict) -> str:
    """Shell com timeout que mata a ARVORE (o legado deixava netos orfaos).
    Windows: grupo novo + taskkill /F /T; Unix: sessao nova + killpg."""
    cmd = str(args["comando"])
    cwd = _resolver(args.get("cwd") or ".")
    if not cwd.is_dir():
        return "[ERRO] cwd nao existe: %s" % cwd
    timeout = min(600, int(args.get("timeout") or 120))

    kwargs: dict = dict(shell=True, cwd=str(cwd), stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True,
                        encoding="utf-8", errors="replace")
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
        proc.communicate()
        return "[ERRO] timeout apos %ds — arvore de processos encerrada" % timeout
    return "[exit=%d]\n--- STDOUT ---\n%s\n--- STDERR ---\n%s" % (
        proc.returncode, (out or "")[:SHELL_STDOUT_MAX],
        (err or "")[:SHELL_STDERR_MAX])


def _memorizar(args: dict) -> str:
    chave = str(args["chave"]).strip()
    memoria.gravar(chave, str(args["valor"]), str(args.get("tags") or ""))
    return "[OK] memorizado: %s" % chave


def _lembrar(args: dict) -> str:
    chave = str(args.get("chave") or "").strip()
    busca = str(args.get("busca") or "").strip()
    if chave:
        valor = memoria.obter(chave)
        return ("%s: %s" % (chave, valor)) if valor is not None else (
            "(nada memorizado com a chave %r)" % chave)
    if not busca:
        return "[ERRO] informe `busca` (texto) ou `chave` (exata)"
    achados = memoria.buscar_inteligente(busca)
    if not achados:
        return "(nada na memoria para %r)" % busca
    return "\n".join("%s: %s%s" % (c, v, (" [%s]" % t) if t else "")
                     for c, v, t in achados)


def _esquecer(args: dict) -> str:
    chave = str(args["chave"]).strip()
    if memoria.apagar(chave):
        return "[OK] esquecido: %s" % chave
    return "(nada memorizado com a chave %r)" % chave


def _mcp(args: dict) -> str:
    return mcp_cliente.chamar(str(args["servidor"]).strip(),
                              str(args.get("tool") or "").strip(),
                              args.get("argumentos")
                              if isinstance(args.get("argumentos"), dict)
                              else None)


# --- previews (o que o usuario ve ao confirmar) -----------------------------
def _preview_editar(args: dict) -> str:
    try:
        p = _resolver(args["caminho"])
        antigo, novo = str(args["texto_antigo"]), str(args["texto_novo"])
        diff = difflib.unified_diff(antigo.splitlines(), novo.splitlines(),
                                    fromfile=p.name, tofile=p.name, lineterm="")
        linhas = list(diff)[2:14]  # sem cabecalho ---/+++; ate 12 linhas
        return "editar %s:\n%s" % (p, "\n".join(linhas))
    except KeyError:
        return "editar (argumentos incompletos)"


# --- registro ---------------------------------------------------------------
class _Tool:
    def __init__(self, impl: Callable[[dict], str], schema: dict,
                 requeridos: tuple, classificar: Callable, preview: Callable):
        self.impl, self.schema = impl, schema
        self.requeridos = requeridos
        self.classificar = classificar   # args -> (kind|None, token|None)
        self.preview = preview           # args -> str


def _schema(nome: str, desc: str, props: dict, req: list) -> dict:
    return {"type": "function", "function": {
        "name": nome, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": req}}}


_S = {"type": "string"}
_I = {"type": "integer"}
_B = {"type": "boolean"}

TOOLS: dict[str, _Tool] = {
    "ler": _Tool(
        _ler,
        _schema("ler", "Le um arquivo de texto com numeros de linha. Use antes de editar.",
                {"caminho": _S, "offset": {**_I, "description": "1a linha (1-based)"},
                 "limite": {**_I, "description": "max de linhas"}}, ["caminho"]),
        ("caminho",), lambda a: (None, None), lambda a: "ler %s" % a.get("caminho")),
    "listar": _Tool(
        _listar,
        _schema("listar", "Lista arquivos/pastas de um diretorio (glob opcional).",
                {"caminho": _S, "padrao": {**_S, "description": "glob, ex. *.py"},
                 "recursivo": _B}, []),
        (), lambda a: (None, None), lambda a: "listar %s" % (a.get("caminho") or ".")),
    "buscar": _Tool(
        _buscar,
        _schema("buscar", "Procura um texto/regex dentro dos arquivos (grep).",
                {"padrao": _S, "raiz": _S, "regex": _B,
                 "glob_arquivos": {**_S, "description": "filtra arquivos, ex. *.py"}},
                ["padrao"]),
        ("padrao",), lambda a: (None, None), lambda a: "buscar '%s'" % a.get("padrao")),
    "escrever": _Tool(
        _escrever,
        _schema("escrever", "Cria/sobrescreve um arquivo de texto (escrita atomica).",
                {"caminho": _S, "conteudo": _S}, ["caminho", "conteudo"]),
        ("caminho", "conteudo"),
        lambda a: (_kind_escrita(_resolver(a["caminho"])), None),
        lambda a: "escrever %s (%d chars)" % (a.get("caminho"),
                                              len(str(a.get("conteudo", ""))))),
    "editar": _Tool(
        _editar,
        _schema("editar", "Substitui um trecho EXATO e unico de um arquivo. "
                          "0 ocorrencias ou mais de 1 sem todas=true retornam erro.",
                {"caminho": _S, "texto_antigo": _S, "texto_novo": _S, "todas": _B},
                ["caminho", "texto_antigo", "texto_novo"]),
        ("caminho", "texto_antigo", "texto_novo"),
        lambda a: (_kind_escrita(_resolver(a["caminho"])), None),
        _preview_editar),
    "shell": _Tool(
        _shell,
        _schema("shell", "Executa um comando no shell do sistema e retorna "
                         "[exit=N] + stdout/stderr. Use p/ rodar testes, git, etc.",
                {"comando": _S, "cwd": _S,
                 "timeout": {**_I, "description": "segundos (default 120)"}},
                ["comando"]),
        ("comando",),
        lambda a: (("git_write" if _cmd_git_write(str(a["comando"])) else "shell"),
                   portao.token_comando(str(a["comando"]))),
        lambda a: "shell$ %s" % a.get("comando")),
    "memorizar": _Tool(
        _memorizar,
        _schema("memorizar", "Guarda um fato duravel na memoria persistente "
                             "do LILO (sobrevive entre sessoes). Use com "
                             "parcimonia, para fatos uteis do usuario/projeto.",
                {"chave": _S, "valor": _S,
                 "tags": {**_S, "description": "palavras-chave opcionais"}},
                ["chave", "valor"]),
        ("chave", "valor"), lambda a: (None, None),
        lambda a: "memorizar %s" % a.get("chave")),
    "lembrar": _Tool(
        _lembrar,
        _schema("lembrar", "Recupera fatos da memoria persistente do LILO: "
                           "por busca textual ou por chave exata.",
                {"busca": _S, "chave": _S}, []),
        (), lambda a: (None, None),
        lambda a: "lembrar %s" % (a.get("busca") or a.get("chave") or "")),
    "esquecer": _Tool(
        _esquecer,
        _schema("esquecer", "Apaga um fato da memoria persistente pela chave "
                            "exata (use lembrar antes p/ conferir a chave).",
                {"chave": _S}, ["chave"]),
        ("chave",), lambda a: (None, None),
        lambda a: "esquecer %s" % a.get("chave")),
    "mcp": _Tool(
        _mcp,
        _schema("mcp", "Acessa um servidor MCP externo configurado pelo "
                       "usuario em LILO_MCP. Sem `tool`: lista as tools do "
                       "servidor. Com `tool`+`argumentos`: executa.",
                {"servidor": _S, "tool": _S,
                 "argumentos": {"type": "object",
                                "description": "argumentos da tool remota"}},
                ["servidor"]),
        ("servidor",), lambda a: ("mcp", None),
        lambda a: "mcp %s.%s" % (a.get("servidor"), a.get("tool") or "(listar)")),
}

SCHEMAS = [t.schema for t in TOOLS.values()]

NEGADO = ("[NEGADO] O usuario recusou esta acao. Nao repita a mesma chamada; "
          "proponha uma alternativa ou pergunte a ele.")


def executar_tool(nome: str, args: dict, perms: portao.Permissoes,
                  confirmar: Callable[[str, str], str]) -> str:
    """O UNICO caminho de execucao de tool do LILO.

    valida -> classifica kind -> portao.decidir -> (confirma no ponto) ->
    executa a implementacao privada -> trunca. `confirmar(kind, preview)`
    devolve 's' (sim, uma vez), 'n' (nao) ou 't' (sempre nesta sessao).
    """
    tool = TOOLS.get(nome)
    if tool is None:
        return "[ERRO] tool desconhecida: %r. Disponiveis: %s" % (
            nome, ", ".join(TOOLS))
    if not isinstance(args, dict):
        return "[ERRO] argumentos invalidos (esperado objeto JSON)"
    faltando = [r for r in tool.requeridos if not str(args.get(r) or "").strip()]
    if faltando:
        return "[ERRO] argumento obrigatorio ausente: %s" % ", ".join(faltando)

    # shell destrutivo: bloqueio duro ANTES de qualquer modo/portao
    if nome == "shell" and _cmd_perigoso(str(args.get("comando", ""))):
        return "[BLOQUEADO] comando na deny-list de destrutivos — nao sera executado em nenhum modo"

    try:
        kind, token = tool.classificar(args)
    except (KeyError, OSError) as e:
        return "[ERRO] argumentos invalidos: %s" % e
    preview = tool.preview(args)

    decisao = portao.decidir(kind, perms, token)
    if decisao == portao.PLANO:
        perms.plano.append((kind or "acao", preview))
        return "[MODO PLANO] acao anotada, NAO executada: %s" % preview
    if decisao == portao.CONFIRMAR:
        resp = (confirmar(kind or "acao", preview) or "n").strip().lower()[:1]
        if resp == "t":
            perms.registrar_grant(kind or "", token)
        elif resp != "s":
            return NEGADO

    try:
        saida = tool.impl(args)
    except Exception as e:  # noqa: BLE001 — erro de tool volta ao modelo
        log.warning("tool %s falhou: %s", nome, e)
        return "[ERRO] %s: %s" % (type(e).__name__, e)

    if len(saida) > LIMITE_RESULTADO:
        saida = saida[:LIMITE_RESULTADO] + "\n[truncado — %d chars omitidos]" % (
            len(saida) - LIMITE_RESULTADO)
    return saida
