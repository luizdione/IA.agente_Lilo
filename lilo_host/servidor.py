"""Servidor MCP HTTP da ponte: tres FastMCP (mcp 1.27) montados numa Starlette.

  GET  /saude                 estado da ponte (JSON)
  POST /conhecimento/mcp      memoria dos projetos, PDF/texto, resumo
  POST /analise/mcp           estatistica, parsers bio, DOCX
  POST /exec/mcp              Python, R, WSL — exige `Authorization: Bearer <token>`
  POST /codigo/mcp            arquivos (ler/escrever/editar/buscar/listar) e PowerShell — mesmo token

Transporte streamable HTTP sem estado e com resposta JSON (o que a Open WebUI e o
Claude Code consomem sem SSE). Protecao contra DNS rebinding ligada, com
`host.docker.internal` na lista: e assim que o container chega ao 127.0.0.1 do host.
Regra de velocidade 5: no maximo 14 tools por grupo.
"""
from __future__ import annotations

import contextlib
import hmac
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route

from . import (__version__, arquivos, biblioteca, bioparsers, docx, estatistica, execucao, pastas,
               projetos, resumir, skills)
from .comum import PORTA, TRABALHO, gpu_reservada

HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*", "host.docker.internal:*"]
ORIGENS = ["http://" + h for h in HOSTS]


def _seguranca() -> TransportSecuritySettings:
    return TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                     allowed_hosts=HOSTS, allowed_origins=ORIGENS)


def _novo(nome: str, instrucoes: str) -> FastMCP:
    return FastMCP(nome, instructions=instrucoes, host="127.0.0.1", port=PORTA,
                   streamable_http_path="/mcp", stateless_http=True, json_response=True,
                   transport_security=_seguranca())


def _json(d: Any) -> str:
    return d if isinstance(d, str) else json.dumps(d, ensure_ascii=False, indent=1)


# ------------------------------------------------------------- conhecimento
def grupo_conhecimento() -> FastMCP:
    srv = _novo("lilo-conhecimento",
                "Memoria dos projetos do dono, leitura de PDF/texto e resumo de arquivos.")

    @srv.tool()
    def memoria_projetos_listar() -> str:
        """Lista os projetos que tem memoria `.project-memory` (nome, pasta, n de arquivos,
        data da ultima atualizacao), do mais recente ao mais antigo."""
        return _json(projetos.listar())

    @srv.tool()
    def memoria_projeto_ler(projeto: str, max_chars: int = 12000) -> str:
        """Le a memoria .md de um projeto (PROJECT_STATE, TASKS, CONTEXT, KNOWLEDGE...).
        `projeto` e o nome devolvido por memoria_projetos_listar."""
        pj = projetos.ler_projeto(projeto)
        if pj is None:
            return "[ERRO] projeto '%s' nao encontrado; use memoria_projetos_listar" % projeto
        return pj.texto(max_chars=max_chars)

    @srv.tool()
    def memoria_buscar(consulta: str, projeto: str = "", limite: int = 20) -> str:
        """Busca um termo na memoria de um projeto (ou de todos, se `projeto` vazio);
        devolve trechos com o nome do projeto e do arquivo."""
        return _json(projetos.buscar(consulta, projeto or None, limite))

    @srv.tool()
    def ler_pdf(caminho: str, pagina_inicial: int = 1, paginas: int = 40) -> str:
        """Texto de um PDF por janela de paginas (ate 40 por chamada). Para PDFs
        longos, chame de novo com `pagina_inicial` maior."""
        return resumir.ler_pdf(caminho, pagina_inicial, paginas)

    @srv.tool()
    def ler_texto(caminho: str, max_chars: int = 12000) -> str:
        """Conteudo de um arquivo de texto (txt, md, csv, log, json, py, R, docx, pdf),
        recortado em inicio+fim se passar de max_chars."""
        return resumir.ler_texto(caminho, max_chars)

    @srv.tool()
    def resumir_arquivo(caminho: str, pergunta: str = "", max_chars: int = 1200) -> str:
        """Resumo de um arquivo feito pelo modelo local `lilo`, opcionalmente guiado por
        uma pergunta. Nao roda com a GPU reservada."""
        return resumir.resumir_arquivo(caminho, pergunta, max_chars)

    @srv.tool()
    def biblioteca_buscar(consulta: str, n: int = 5) -> str:
        """Busca hibrida (bge-m3 + BM25) na biblioteca de PDFs do dono (~1.100 artigos):
        os n documentos mais relevantes, com titulo, pagina, trecho e caminho do PDF."""
        return _json(biblioteca.buscar(consulta, n))

    @srv.tool()
    def biblioteca_status() -> str:
        """Quantos PDFs estao indexados, falhas, trechos e o progresso da indexacao em curso."""
        return _json(biblioteca.status())

    @srv.tool()
    def skills_listar(filtro: str = "", limite: int = 30) -> str:
        """Catalogo das skills do dono (Claude Code: proprias, bioinformatica e plugins), lidas
        no lugar. Sem filtro lista as proprias; com filtro ('qpcr', 'docking', 'git') busca em
        todas (sao ~850)."""
        return _json(skills.listar(filtro, limite))

    @srv.tool()
    def skill_ler(nome: str) -> str:
        """Instrucoes completas (SKILL.md) e arquivos de uma skill. Siga-as como roteiro; os
        scripts dela rodam com skill_rodar (preset Analise)."""
        return skills.ler(nome)

    @srv.tool()
    def pasta_listar(caminho: str, profundidade: int = 2) -> str:
        """Arvore de uma pasta do computador (ate 6 niveis) com tamanhos. E assim que o dono
        "anexa" uma pasta: ele cita o caminho e voce lista, busca (pasta_buscar) e le (ler_texto)."""
        return pastas.listar(caminho, profundidade)

    @srv.tool()
    def pasta_buscar(caminho: str, termo: str, extensoes: str = "") -> str:
        """Procura um termo nos arquivos de texto de uma pasta (arquivo, linha, trecho);
        `extensoes` como ".py,.md" restringe."""
        return _json(pastas.buscar(caminho, termo, extensoes))

    @srv.tool()
    def repos_listar() -> str:
        """Repositorios git do dono em C:\\GitHub: ramo, arquivos alterados e ultimo commit.
        Para agir neles use executar_git (preset Analise)."""
        return _json(pastas.repos_listar())

    @srv.tool()
    def pasta_escolher(titulo: str = "LILO: escolha a pasta") -> str:
        """Abre o seletor de pasta do Windows na tela do dono e devolve o caminho escolhido
        (ou "[cancelado]"). Use quando ele pedir para escolher/selecionar uma pasta ou diretorio;
        depois trabalhe nela com pasta_listar, pasta_buscar e ler_texto."""
        return pastas.escolher(titulo)

    return srv


# ------------------------------------------------------------------ analise
def grupo_analise() -> FastMCP:
    srv = _novo("lilo-analise",
                "Estatistica (pingouin/statsmodels), parsers de logs bio e DOCX. "
                "Dados: listas de numeros ou CSV (csv + coluna [+ grupo]).")

    @srv.tool()
    def estat_descrever(csv: str = "", coluna: str = "", grupo: str = "",
                        valores: list[float] | None = None) -> str:
        """Descritiva (n, media, DP, EP, IC95%, mediana, quartis, min, max) de uma coluna
        de CSV (por grupo, se `grupo`) ou de uma lista de numeros."""
        return _json(estatistica.executar("descrever", csv=csv, coluna=coluna, grupo=grupo, valores=valores))

    @srv.tool()
    def estat_normalidade(csv: str = "", coluna: str = "", grupo: str = "",
                          valores: list[float] | None = None) -> str:
        """Shapiro-Wilk (+ assimetria e curtose) por amostra."""
        return _json(estatistica.executar("normalidade", csv=csv, coluna=coluna, grupo=grupo, valores=valores))

    @srv.tool()
    def estat_teste_t(csv: str = "", coluna: str = "", grupo: str = "",
                      valores: list[float] | None = None, valores_b: list[float] | None = None,
                      pareado: bool = False, var_igual: bool = False) -> str:
        """Teste t entre 2 amostras: Welch por padrao, Student com var_igual, ou pareado.
        Devolve t, gl, p, IC95% da diferenca e d de Cohen."""
        return _json(estatistica.executar("teste_t", csv=csv, coluna=coluna, grupo=grupo, valores=valores,
                                          valores_b=valores_b, pareado=pareado, var_igual=var_igual))

    @srv.tool()
    def estat_mann_whitney(csv: str = "", coluna: str = "", grupo: str = "",
                           valores: list[float] | None = None, valores_b: list[float] | None = None) -> str:
        """Mann-Whitney U (nao parametrico, 2 amostras independentes)."""
        return _json(estatistica.executar("mann_whitney", csv=csv, coluna=coluna, grupo=grupo,
                                          valores=valores, valores_b=valores_b))

    @srv.tool()
    def estat_anova(csv: str = "", coluna: str = "", grupo: str = "", nao_parametrico: bool = False) -> str:
        """ANOVA de uma via com Tukey HSD (ou Kruskal-Wallis com pos-hoc, se nao_parametrico)
        sobre `coluna` de um CSV separada por `grupo` (2+ grupos)."""
        return _json(estatistica.executar("anova", csv=csv, coluna=coluna, grupo=grupo,
                                          nao_parametrico=nao_parametrico))

    @srv.tool()
    def estat_correlacao(csv: str = "", coluna: str = "", coluna_b: str = "", metodo: str = "pearson",
                         valores: list[float] | None = None, valores_b: list[float] | None = None) -> str:
        """Correlacao de Pearson, Spearman ou Kendall entre duas series pareadas
        (duas colunas de um CSV ou duas listas)."""
        if csv and coluna_b:
            r1 = estatistica.executar("descrever", csv=csv, coluna=coluna)
            if isinstance(r1, str):
                return r1
            import pandas as pd
            from .comum import resolver
            df = pd.read_csv(resolver(csv), sep=None, engine="python")
            valores, valores_b, csv = list(df[coluna]), list(df[coluna_b]), ""
        return _json(estatistica.executar("correlacao", csv=csv, coluna=coluna, valores=valores,
                                          valores_b=valores_b, metodo=metodo))

    @srv.tool()
    def estat_qui_quadrado(tabela: list[list[float]], yates: bool = False) -> str:
        """Qui-quadrado de independencia numa tabela de contingencia (lista de linhas) + V de Cramer."""
        try:
            return _json(estatistica.qui_quadrado(tabela, yates))
        except ValueError as e:
            return "[ERRO] %s" % e

    @srv.tool()
    def bio_parse_log(caminho: str, tipo: str = "auto") -> str:
        """Tabela compacta de um log de bioinformatica: Vina (docking), qPCR, FastQC ou
        resumo de VCF (`tipo` auto-detectado; .gz aceito)."""
        from .comum import resolver
        try:
            return bioparsers.parse_bio_log(str(resolver(caminho)), tipo)
        except Exception as e:  # noqa: BLE001
            return "[ERRO] %s: %s" % (type(e).__name__, e)

    @srv.tool()
    def docx_ler(caminho: str) -> str:
        """Texto de um .docx (titulos marcados com #, tabelas em pipe)."""
        return docx.ler(caminho)

    @srv.tool()
    def docx_escrever(caminho: str, markdown: str, titulo: str = "") -> str:
        """Grava um .docx a partir de Markdown simples (titulos, paragrafos, listas, tabelas)."""
        return docx.escrever(caminho, markdown, titulo)

    return srv


# --------------------------------------------------------------------- exec
def grupo_exec() -> FastMCP:
    srv = _novo("lilo-exec",
                "Executa Python (env datascience), R e bash do WSL no host, com tempo limite. "
                "Mostre sempre o codigo e a saida tal como vieram.")

    @srv.tool()
    def executar_python(codigo: str, timeout: int = 120, cwd: str = "") -> str:
        """Roda codigo Python no env datascience (pandas, scipy, Biopython, matplotlib...).
        Saida: [exit=N] + STDOUT/STDERR recortados. cwd padrao: pasta de trabalho da ponte."""
        return execucao.executar_python(codigo, timeout, cwd or None)

    @srv.tool()
    def executar_r(codigo: str, timeout: int = 180, cwd: str = "") -> str:
        """Roda codigo R (Rscript 4.5 do env datascience)."""
        return execucao.executar_r(codigo, timeout, cwd or None)

    @srv.tool()
    def executar_wsl(comando: str, timeout: int = 120) -> str:
        """Roda um comando bash no WSL (Ubuntu)."""
        return execucao.executar_wsl(comando, timeout)

    @srv.tool()
    def executar_git(repo: str, argumentos: str, timeout: int = 120) -> str:
        """git num repositorio de C:\\GitHub (nome da pasta ou caminho): status, log, diff, add,
        commit, checkout -b, pull, push... Operacoes destrutivas (--force, reset --hard,
        clean -f, branch -D) sao bloqueadas. Mostre a saida como veio."""
        return execucao.executar_git(repo, argumentos, timeout)

    @srv.tool()
    def skill_rodar(nome: str, script: str, argumentos: str = "", cwd: str = "", timeout: int = 300) -> str:
        """Roda um script da pasta de uma skill do dono, ex.: skill_rodar("git_dione",
        "git_dione_sync.py", "--status", cwd="C:/GitHub/Paper_X"). .py no env datascience,
        .R, .ps1 ou .sh (WSL). Leia a skill antes (skill_ler) para saber os argumentos."""
        alvo = skills.script(nome, script)
        if isinstance(alvo, str):
            return alvo
        return execucao.rodar_script(alvo, argumentos, cwd or None, timeout)

    return srv


# ------------------------------------------------------------------- codigo
def grupo_codigo() -> FastMCP:
    srv = _novo("lilo-codigo",
                "Arquivos de texto/codigo do host: ler numerado, escrever, editar com diff, buscar "
                "(grep), listar (glob) e PowerShell. Escrita e cwd so em E:\\data\\lilo\\trabalho, "
                "C:\\GitHub e OneDrive\\Data_Science\\Projetos. Mostre o diff e a saida como vieram.")

    @srv.tool()
    def arquivo_ler(caminho: str, inicio: int = 1, linhas: int = 200) -> str:
        """Le texto/codigo com linhas numeradas (N<TAB>texto; os numeros nao fazem parte do
        arquivo). Ate 400 linhas ou 16000 caracteres por chamada; para mais, chame de novo com
        inicio maior. PDF/DOCX: use ler_pdf / ler_texto."""
        return arquivos.ler(caminho, inicio, linhas)

    @srv.tool()
    def arquivo_escrever(caminho: str, conteudo: str, sobrescrever: bool = False) -> str:
        """Cria um arquivo UTF-8 (cria as pastas). Se ja existe, so grava com sobrescrever=true e
        devolve o diff. Para mudar parte de um arquivo use arquivo_editar."""
        return arquivos.escrever(caminho, conteudo, sobrescrever)

    @srv.tool()
    def arquivo_editar(caminho: str, antigo: str, novo: str, todas: bool = False) -> str:
        """Troca o trecho EXATO `antigo` por `novo` (inclua 2-3 linhas de contexto para ser unico).
        Devolve o diff unificado. Falha se `antigo` nao existe ou aparece mais de uma vez (use
        todas=true para trocar todas)."""
        return arquivos.editar(caminho, antigo, novo, todas)

    @srv.tool()
    def arquivo_buscar(padrao: str, caminho: str = ".", glob: str = "", regex: bool = False,
                       contexto: int = 0, max_resultados: int = 40) -> str:
        """Procura texto nos arquivos (como grep -rn): `arquivo:linha: texto`. glob='*.py'
        restringe; contexto=2 mostra linhas ao redor. Ignora .git, node_modules, __pycache__,
        .venv, binarios e arquivos > 2 MB."""
        return arquivos.buscar(padrao, caminho, glob, regex, contexto, max_resultados)

    @srv.tool()
    def arquivo_listar(padrao: str = "**/*", caminho: str = ".", max_resultados: int = 200) -> str:
        """Lista arquivos por glob ('**/*.py'), caminho relativo e tamanho. Para a arvore de uma
        pasta use pasta_listar."""
        return arquivos.listar(padrao, caminho, max_resultados)

    @srv.tool()
    def executar_powershell(comando: str, cwd: str = "", timeout: int = 120) -> str:
        """Roda um comando PowerShell no Windows (pytest, git, python -m ...). cwd dentro das
        pastas permitidas. Saida: [exit=N em S s] + STDOUT/STDERR recortados. Comandos
        destrutivos, codificados ou de internet sao bloqueados."""
        return execucao.executar_powershell(comando, timeout, cwd or None)

    return srv


# ---------------------------------------------------------------------- app
class _TokenExec:
    """Middleware ASGI: /exec/* e /codigo/* so com `Authorization: Bearer <token>` (401 caso contrario)."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith(("/exec", "/codigo")):
            auth = ""
            for k, v in scope.get("headers", []):
                if k == b"authorization":
                    auth = v.decode("latin-1")
            ok = bool(self.token) and hmac.compare_digest(auth, "Bearer " + self.token)
            if not ok:
                resp = JSONResponse({"erro": "grupos exec e codigo exigem Authorization: Bearer <token>"},
                                    status_code=401)
                await resp(scope, receive, send)
                return
        await self.app(scope, receive, send)


_PROXY_CAB = ("content-type", "accept", "mcp-session-id", "last-event-id", "mcp-protocol-version")


async def literatura(request: Request) -> Response:
    """Proxy do Docker MCP Gateway (paper-search): /literatura/mcp -> 127.0.0.1:8811/mcp.

    O gateway recusa qualquer Host que nao seja localhost (anti DNS-rebinding) e exige o
    token MCP_GATEWAY_AUTH_TOKEN; a ponte reescreve o Host, injeta o token e repassa o
    streaming (SSE) tal como vem. Se o gateway estiver parado, responde 503.
    """
    from .comum import GATEWAY, token_gateway
    cab = {k: v for k, v in request.headers.items() if k.lower() in _PROXY_CAB}
    cab["host"] = GATEWAY.split("://", 1)[-1]
    cab["authorization"] = "Bearer " + token_gateway(gerar=False)
    corpo = await request.body()
    cli = httpx.AsyncClient(timeout=httpx.Timeout(120.0, read=600.0))
    try:
        req = cli.build_request(request.method, GATEWAY + "/mcp", headers=cab, content=corpo)
        resp = await cli.send(req, stream=True)
    except httpx.HTTPError as e:
        await cli.aclose()
        return JSONResponse({"erro": "gateway de literatura fora do ar (%s); suba com lilo.ps1 gateway up" % e},
                            status_code=503)
    saida = {k: v for k, v in resp.headers.items()
             if k.lower() in ("content-type", "mcp-session-id", "mcp-protocol-version", "cache-control")}

    async def corpo_resp():
        try:
            async for pedaco in resp.aiter_raw():
                yield pedaco
        finally:
            await resp.aclose()
            await cli.aclose()

    return StreamingResponse(corpo_resp(), status_code=resp.status_code, headers=saida)


def criar_app(token: str) -> Starlette:
    grupos = {"conhecimento": grupo_conhecimento(), "analise": grupo_analise(), "exec": grupo_exec(),
              "codigo": grupo_codigo()}
    subapps = {nome: srv.streamable_http_app() for nome, srv in grupos.items()}

    async def saude(_: Request) -> JSONResponse:
        from .comum import GATEWAY
        n = {nome: len(await_tools(srv)) for nome, srv in grupos.items()}
        try:
            async with httpx.AsyncClient(timeout=3.0) as cli:
                gw = (await cli.get(GATEWAY + "/mcp")).status_code in (401, 405, 400, 406)
        except httpx.HTTPError:
            gw = False
        return JSONResponse({"ok": True, "versao": __version__, "porta": PORTA, "grupos": n,
                             "gpu_reservada": gpu_reservada(), "trabalho": str(TRABALHO),
                             "exec_com_token": bool(token), "gateway_literatura": gw})

    def aquecer_biblioteca():
        # O embedder de consulta (bge-m3 na CPU) leva ~30 s para subir dentro do servidor;
        # carregado em segundo plano no `up`, a 1a busca do dono nao paga esse tempo.
        if (biblioteca.INDICE / "biblioteca.db").exists():
            try:
                biblioteca.embedder_consulta()
            except Exception:  # noqa: BLE001 — sem modelo local, a 1a busca carrega (ou falha) sozinha
                pass

    @contextlib.asynccontextmanager
    async def vida(_app):
        # Sub-apps montados nao recebem o lifespan da Starlette pai: abrimos
        # os gerenciadores de sessao aqui.
        import threading
        threading.Thread(target=aquecer_biblioteca, daemon=True).start()
        async with contextlib.AsyncExitStack() as pilha:
            for srv in grupos.values():
                await pilha.enter_async_context(srv.session_manager.run())
            yield

    rotas = ([Route("/saude", saude), Route("/literatura/mcp", literatura, methods=["GET", "POST", "DELETE"])]
             + [Mount("/" + nome, app=sub) for nome, sub in subapps.items()])
    app = Starlette(routes=rotas, lifespan=vida)
    app.state.grupos = grupos
    return _TokenExec(app, token)


def await_tools(srv: FastMCP) -> list:
    return srv._tool_manager.list_tools()
