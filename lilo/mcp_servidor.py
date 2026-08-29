"""LILO como SERVIDOR MCP (v13.4) — `lilo mcp-serve`.

Expoe as tools do LILO (ler/ler_pdf/escrever/editar/listar/buscar/shell/
memorizar/lembrar/esquecer) a clientes MCP como o Claude Desktop — repondo a ponte que
o legado tinha, sem violar a regra anti-inchaco: e um SUBCOMANDO do mesmo
binario (nao um entry point novo) e TODA execucao passa pelo mesmo
`tools.executar_tool` (choke-point + portao).

Permissoes num contexto sem stdin interativo: o modo vem de
LILO_MCP_SERVE_MODE (default `accept_edits` — leituras e writes na allow-list
passam; shell/git/fora-da-lista viram [NEGADO] instrutivo, porque nao ha como
perguntar). LILO_MCP_SERVE_MODE=auto libera shell (git_write NUNCA — e o
proprio cliente MCP, ex. Claude Desktop, ja tem a camada de aprovacao dele).
A tool `mcp` NAO e reexposta (proxy-de-proxy = loops).

v13.8 — `delegar`: a excecao consciente ao padrao wrapper->_exec. Ela nao e
uma tool do registro; ela roda O LOOP inteiro do LILO (agente.executar_tarefa
sobre o Ollama local) e devolve a resposta final — e o loop, por construcao,
executa TODA acao pelo mesmo executar_tool + portao acima. E o que permite ao
Claude Code/Desktop despachar tarefas ao modelo LOCAL: gratis, offline,
privado. Anti-recursao: nao configure o proprio LILO em LILO_MCP (delegar ->
loop -> tool mcp -> lilo seria um laco; a allow-list vazia ja impede).

Config no Claude Desktop (claude_desktop_config.json):
    "mcpServers": {"lilo": {"command": "python",
                            "args": ["-m", "lilo", "mcp-serve"],
                            "cwd": "C:\\\\github\\\\LILO"}}

O servidor tambem ANCORA o PATH no ambiente do interpretador que o roda
(v13.11) — registre o LILO com o python do ambiente onde estao os seus
pacotes, e o que ele rodar usara esse mesmo ambiente.

Dependencia OPCIONAL: pip install mcp.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from lilo import config, tools
from lilo.portao import MODOS, Permissoes

NEGADO_DICA = (" (mcp-serve nao tem confirmacao interativa — rode o servidor "
               "com LILO_MCP_SERVE_MODE=auto para liberar, exceto git)")


def _perms() -> Permissoes:
    modo = config.get_env("LILO_MCP_SERVE_MODE", "accept_edits").strip().lower()
    return Permissoes(modo=modo if modo in MODOS else "accept_edits")


def _negar(kind: str, preview: str) -> str:
    return "n"


def _exec(nome: str, args: dict) -> str:
    """UNICO caminho: choke-point de sempre, com dica quando negar."""
    saida = tools.executar_tool(nome, args, _perms(), _negar)
    if saida.startswith("[NEGADO]"):
        saida += NEGADO_DICA
    return saida


# Wrappers finos e tipados (o schema MCP nasce das assinaturas). Nada aqui
# executa por conta propria — tudo delega ao _exec.
def ler(caminho: str, offset: int = 1, limite: int = 2000) -> str:
    """Le um arquivo de texto com numeros de linha."""
    return _exec("ler", {"caminho": caminho, "offset": offset,
                         "limite": limite})


def ler_pdf(caminho: str, pagina_inicial: int = 1, paginas: int = 40) -> str:
    """Extrai o texto de um arquivo PDF, paginado (dep. opcional PyMuPDF)."""
    return _exec("ler_pdf", {"caminho": caminho,
                             "pagina_inicial": pagina_inicial,
                             "paginas": paginas})


def listar(caminho: str = ".", padrao: str = "*", recursivo: bool = False) -> str:
    """Lista arquivos/pastas de um diretorio (glob opcional)."""
    return _exec("listar", {"caminho": caminho, "padrao": padrao,
                            "recursivo": recursivo})


def buscar(padrao: str, raiz: str = ".", regex: bool = False,
           glob_arquivos: str = "") -> str:
    """Procura texto/regex dentro dos arquivos (grep com ignore-list)."""
    return _exec("buscar", {"padrao": padrao, "raiz": raiz, "regex": regex,
                            "glob_arquivos": glob_arquivos})


def escrever(caminho: str, conteudo: str) -> str:
    """Cria/sobrescreve um arquivo de texto (escrita atomica)."""
    return _exec("escrever", {"caminho": caminho, "conteudo": conteudo})


def editar(caminho: str, texto_antigo: str, texto_novo: str,
           todas: bool = False) -> str:
    """Substitui um trecho EXATO e unico de um arquivo."""
    return _exec("editar", {"caminho": caminho, "texto_antigo": texto_antigo,
                            "texto_novo": texto_novo, "todas": todas})


def shell(comando: str, cwd: str = ".", timeout: int = 120) -> str:
    """Executa um comando no shell ([exit=N] + stdout/stderr)."""
    return _exec("shell", {"comando": comando, "cwd": cwd, "timeout": timeout})


def memorizar(chave: str, valor: str, tags: str = "") -> str:
    """Guarda um fato duravel na memoria persistente do LILO."""
    return _exec("memorizar", {"chave": chave, "valor": valor, "tags": tags})


def lembrar(busca: str = "", chave: str = "") -> str:
    """Recupera fatos da memoria (busca semantica/LIKE ou chave exata)."""
    return _exec("lembrar", {"busca": busca, "chave": chave})


def esquecer(chave: str) -> str:
    """Apaga um fato da memoria persistente pela chave exata."""
    return _exec("esquecer", {"chave": chave})


def _criar_cliente():
    """Isolado p/ monkeypatch nos testes (padrao _importar_fitz do tools)."""
    from lilo.cliente import ClienteOllama
    return ClienteOllama()


def delegar(tarefa: str, modelo: str = "") -> str:
    """Executa uma tarefa COMPLETA no agente LILO local (loop + tools +
    portao, sobre o Ollama DESTA maquina) e devolve a resposta final.
    Use para despachar trabalho simples/privado/em lote ao modelo local:
    gratis e offline. `modelo` opcional troca o modelo Ollama só nesta
    tarefa (ex. um mais leve para tarefas triviais)."""
    import os
    from pathlib import Path

    from lilo import agente

    # Claude Code exporta CLAUDE_PROJECT_DIR p/ servidores stdio; ancora o
    # contexto do agente delegado no projeto certo (o cwd do processo do
    # servidor nao e garantido).
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    msgs = [{"role": "system", "content": agente.montar_system(raiz)}]
    resposta, _ = agente.executar_tarefa(
        tarefa, msgs, _perms(), cliente=_criar_cliente(),
        ui=agente.UI(), modelo=modelo or None)
    return resposta


WRAPPERS = {f.__name__: f for f in
            (ler, ler_pdf, listar, buscar, escrever, editar, shell,
             memorizar, lembrar, esquecer, delegar)}


def _criar_servidor():
    """mcp 2.x renomeou FastMCP -> MCPServer; suportamos as duas geracoes."""
    try:
        from mcp.server.mcpserver import MCPServer  # mcp >= 2
        return MCPServer("lilo")
    except ImportError:
        from mcp.server.fastmcp import FastMCP      # mcp 1.x
        return FastMCP("lilo")


def alinhar_path_do_ambiente(ambiente: dict | None = None) -> str:
    """Ancora o servidor no ambiente do interpretador que o executa (v13.11).

    O Claude Code sobe o `mcp-serve` SEM ativar conda/venv: um `python ...`
    disparado pela tool `shell` cairia no interpretador do PATH herdado —
    tipicamente OUTRO ambiente, sem os pacotes do usuario (no caso do dono,
    os de bioinformatica ficam no env `datascience`). Poe a pasta DESTE
    interpretador (e o Scripts/bin dela) na FRENTE do PATH, entao o que o
    LILO roda usa o MESMO ambiente com que foi registrado.

    Idempotente. Retorna o PATH resultante.
    """
    env = os.environ if ambiente is None else ambiente
    # SEM resolve(): `bin/python` de um venv/env e um LINK para o interpretador
    # base — resolver apontaria o PATH justamente para o ambiente errado.
    base = Path(sys.executable).parent
    extras = [base, base / ("Scripts" if os.name == "nt" else "bin")]
    atual = [p for p in (env.get("PATH") or "").split(os.pathsep) if p]
    alvo = [str(d) for d in extras]
    # remove ocorrencias antigas antes de prefixar: se o diretorio ja estava
    # no PATH mas DEPOIS de outro python, ele perderia a disputa.
    env["PATH"] = os.pathsep.join(alvo + [p for p in atual if p not in alvo])
    return env["PATH"]


def main() -> int:
    alinhar_path_do_ambiente()
    try:
        srv = _criar_servidor()
    except ImportError:
        print("[ERRO] pacote 'mcp' nao instalado — rode: pip install mcp")
        return 1
    for fn in WRAPPERS.values():
        srv.tool()(fn)
    srv.run()  # stdio; retorna quando o cliente desconecta
    return 0
