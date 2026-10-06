"""Ponte lilo-host: endpoints, grupos, token do exec e protecao de Host (sem rede)."""
from __future__ import annotations

import asyncio
import contextlib
import json

import httpx
import pytest

from lilo_host.servidor import criar_app

TOKEN = "segredo-de-teste"
BASE = "http://127.0.0.1:8790"
RPC_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
CAB = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@contextlib.asynccontextmanager
async def _cliente(app):
    # Sub-apps montados dependem do lifespan da Starlette pai (gerenciadores de sessao).
    async with app.app.router.lifespan_context(app.app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE) as c:
            yield c


def _rodar(coro):
    return asyncio.run(coro)


@pytest.fixture
def app():
    # Por teste: o gerenciador de sessao do mcp so aceita um `run()` por instancia.
    return criar_app(TOKEN)


def _tools(resp: httpx.Response) -> list[str]:
    assert resp.status_code == 200, resp.text[:300]
    corpo = resp.json()
    assert "result" in corpo, corpo
    return [t["name"] for t in corpo["result"]["tools"]]


def test_saude_e_grupos(app):
    async def go():
        async with _cliente(app) as c:
            r = await c.get("/saude")
            assert r.status_code == 200
            d = r.json()
            assert d["ok"] and d["grupos"] == {"conhecimento": 8, "analise": 10, "exec": 3}
            assert all(n <= 13 for n in d["grupos"].values())  # regra de velocidade 5
    _rodar(go())


def test_tools_list_por_grupo(app):
    async def go():
        async with _cliente(app) as c:
            con = _tools(await c.post("/conhecimento/mcp", json=RPC_LIST, headers=CAB))
            ana = _tools(await c.post("/analise/mcp", json=RPC_LIST, headers=CAB))
            assert "memoria_projetos_listar" in con and "ler_pdf" in con
            assert "estat_teste_t" in ana and "bio_parse_log" in ana
            assert not set(con) & set(ana)
    _rodar(go())


def test_exec_exige_token(app):
    async def go():
        async with _cliente(app) as c:
            sem = await c.post("/exec/mcp", json=RPC_LIST, headers=CAB)
            assert sem.status_code == 401
            errado = await c.post("/exec/mcp", json=RPC_LIST,
                                  headers={**CAB, "Authorization": "Bearer outro"})
            assert errado.status_code == 401
            com = await c.post("/exec/mcp", json=RPC_LIST,
                               headers={**CAB, "Authorization": "Bearer " + TOKEN})
            assert set(_tools(com)) == {"executar_python", "executar_r", "executar_wsl"}
    _rodar(go())


def test_host_docker_internal_aceito_e_host_estranho_recusado(app):
    async def go():
        async with _cliente(app) as c:
            ok = await c.post("/conhecimento/mcp", json=RPC_LIST,
                              headers={**CAB, "Host": "host.docker.internal:8790"})
            assert ok.status_code == 200
            ruim = await c.post("/conhecimento/mcp", json=RPC_LIST,
                                headers={**CAB, "Host": "evil.example:8790"})
            assert ruim.status_code == 421
    _rodar(go())


def test_chamada_real_memoria_buscar(app, tmp_path, monkeypatch):
    raiz = tmp_path / "raiz"
    (raiz / "proj" / ".project-memory").mkdir(parents=True)
    (raiz / "proj" / ".project-memory" / "PROJECT_STATE.md").write_text(
        "# Estado\nO termo UNICO-XYZ aparece aqui.", encoding="utf-8")
    monkeypatch.setenv("LILO_PROJETOS_RAIZES", str(raiz))
    from lilo_host import projetos
    projetos.mapa(forcar=True)
    corpo = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "memoria_buscar", "arguments": {"consulta": "unico-xyz"}}}

    async def go():
        async with _cliente(app) as c:
            r = await c.post("/conhecimento/mcp", json=corpo, headers=CAB)
            assert r.status_code == 200, r.text[:300]
            texto = r.json()["result"]["content"][0]["text"]
            hits = json.loads(texto)
            assert hits and hits[0]["projeto"] == "proj" and hits[0]["arquivo"] == "PROJECT_STATE.md"
    _rodar(go())
