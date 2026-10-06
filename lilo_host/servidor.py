"""Servidor MCP HTTP da ponte: tres FastMCP (mcp 1.27) montados numa Starlette.

  GET  /saude                 estado da ponte (JSON)
  POST /conhecimento/mcp      memoria dos projetos, PDF/texto, resumo
  POST /analise/mcp           estatistica, parsers bio, DOCX
  POST /exec/mcp              Python, R, WSL — exige `Authorization: Bearer <token>`

Transporte streamable HTTP sem estado e com resposta JSON (o que a Open WebUI e o
Claude Code consomem sem SSE). Protecao contra DNS rebinding ligada, com
`host.docker.internal` na lista: e assim que o container chega ao 127.0.0.1 do host.
Regra de velocidade 5: no maximo 13 tools por grupo.
"""
from __future__ import annotations

import contextlib
import hmac
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from . import __version__, biblioteca, bioparsers, docx, estatistica, execucao, projetos, resumir
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

    return srv


# ---------------------------------------------------------------------- app
class _TokenExec:
    """Middleware ASGI: /exec/* so com `Authorization: Bearer <token>` (401 caso contrario)."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/exec"):
            auth = ""
            for k, v in scope.get("headers", []):
                if k == b"authorization":
                    auth = v.decode("latin-1")
            ok = bool(self.token) and hmac.compare_digest(auth, "Bearer " + self.token)
            if not ok:
                resp = JSONResponse({"erro": "grupo exec exige Authorization: Bearer <token>"},
                                    status_code=401)
                await resp(scope, receive, send)
                return
        await self.app(scope, receive, send)


def criar_app(token: str) -> Starlette:
    grupos = {"conhecimento": grupo_conhecimento(), "analise": grupo_analise(), "exec": grupo_exec()}
    subapps = {nome: srv.streamable_http_app() for nome, srv in grupos.items()}

    async def saude(_: Request) -> JSONResponse:
        n = {nome: len(await_tools(srv)) for nome, srv in grupos.items()}
        return JSONResponse({"ok": True, "versao": __version__, "porta": PORTA, "grupos": n,
                             "gpu_reservada": gpu_reservada(), "trabalho": str(TRABALHO),
                             "exec_com_token": bool(token)})

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

    rotas = [Route("/saude", saude)] + [Mount("/" + nome, app=sub) for nome, sub in subapps.items()]
    app = Starlette(routes=rotas, lifespan=vida)
    app.state.grupos = grupos
    return _TokenExec(app, token)


def await_tools(srv: FastMCP) -> list:
    return srv._tool_manager.list_tools()
