"""Testes da v13.2: busca semantica na memoria + sumarizacao de janela."""
import sqlite3

import pytest

from lilo import agente, config, memoria
from lilo.cliente import ClienteOllama
from tests.conftest import FakeOllama, resposta_texto


@pytest.fixture(autouse=True)
def _memoria_isolada(tmp_path, monkeypatch):
    monkeypatch.setenv("LILO_MEMORIA_DB", str(tmp_path / "memoria.db"))


# --- busca semantica --------------------------------------------------------
def _embedder_fake(vetores: dict):
    """Retorna um _embed fake: texto contendo a chave do dict -> vetor."""
    def _fake(texto: str):
        for marca, vetor in vetores.items():
            if marca in texto:
                return vetor
        return [0.0, 0.0, 1.0]
    return _fake


def test_semantica_ranqueia_por_cosseno(monkeypatch):
    monkeypatch.setattr(memoria, "_embed", _embedder_fake({
        "gpu": [1.0, 0.0, 0.0],
        "editor": [0.0, 1.0, 0.0],
        "placa de video": [0.9, 0.1, 0.0],   # proximo de "gpu"
    }))
    memoria.gravar("gpu", "RTX 3060")
    memoria.gravar("editor", "PyCharm")
    achados = memoria.buscar_semantica("placa de video")
    assert achados and achados[0][0] == "gpu"       # cosseno alto vence
    assert all(c != "editor" for c, _, _ in achados)  # ortogonal fica fora


def test_inteligente_mescla_semantica_e_like(monkeypatch):
    monkeypatch.setattr(memoria, "_embed", _embedder_fake({
        "gpu": [1.0, 0.0, 0.0],
        "consulta_gpu": [0.95, 0.05, 0.0],
    }))
    memoria.gravar("gpu", "RTX 3060")
    memoria.gravar("caminho_dados", "D:\\sequencias contem consulta_gpu nao")
    achados = memoria.buscar_inteligente("consulta_gpu")
    chaves = [c for c, _, _ in achados]
    assert chaves[0] == "gpu"                 # semantica primeiro
    assert "caminho_dados" in chaves          # LIKE completa
    assert len(chaves) == len(set(chaves))    # sem duplicatas


def test_fallback_like_quando_embedder_fora(monkeypatch):
    monkeypatch.setattr(memoria, "_embed", lambda t: None)
    memoria.gravar("gpu", "RTX 3060")
    assert memoria.buscar_semantica("gpu") == []
    assert memoria.buscar_inteligente("3060")[0][0] == "gpu"  # LIKE segura


def test_migracao_adiciona_coluna_embedding(tmp_path, monkeypatch):
    db = tmp_path / "velho.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE kv (chave TEXT PRIMARY KEY, valor TEXT NOT NULL,"
                " tags TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL,"
                " atualizado_em TEXT NOT NULL)")
    con.execute("INSERT INTO kv VALUES ('a', '1', '', 'x', 'x')")
    con.commit()
    con.close()
    monkeypatch.setenv("LILO_MEMORIA_DB", str(db))
    monkeypatch.setattr(memoria, "_embed", lambda t: [1.0, 0.0])
    memoria.gravar("b", "2")                       # nao explode no schema velho
    assert memoria.obter("a") == "1"
    assert memoria.buscar_semantica("b")[0][0] == "b"


# --- sumarizacao de janela --------------------------------------------------
def _historico_grande():
    msgs = [{"role": "system", "content": "s"},
            {"role": "user", "content": "pedido original"}]
    for i in range(12):
        msgs.append({"role": "user", "content": "pergunta %d " % i + "x" * 1200})
        msgs.append({"role": "assistant", "content": "resposta %d " % i + "y" * 1200})
    return msgs


def test_resumo_substitui_miolo(monkeypatch):
    # orcamento em que a CAUDA cabe mas o historico inteiro nao — o cenario
    # que o resumo resolve sem precisar da poda
    monkeypatch.setenv("LILO_NUM_CTX", "8192")
    monkeypatch.setenv("LILO_MAX_TOKENS", "256")
    fake = FakeOllama([resposta_texto("RESUMO_SINTETICO dos fatos")])
    cliente = ClienteOllama(transport=fake)
    podado = agente.ajustar_janela(_historico_grande(), cliente=cliente)
    corpo = " ".join(m.get("content") or "" for m in podado)
    assert agente.RESUMO_MARCA in corpo
    assert "RESUMO_SINTETICO" in corpo
    assert podado[0]["role"] == "system"
    assert podado[1]["content"] == "pedido original"
    orcamento = config.num_ctx() - config.max_tokens() - 1024
    assert sum(agente._tok(m) for m in podado) <= orcamento
    # o resumidor foi chamado SEM tools e com o modelo fast
    payload = fake.chamadas[0][1]
    assert "tools" not in payload
    assert payload["model"] == config.modelo_fast()


def test_resumo_desligado_cai_na_poda(monkeypatch):
    monkeypatch.setenv("LILO_NUM_CTX", "2048")
    monkeypatch.setenv("LILO_MAX_TOKENS", "256")
    monkeypatch.setenv("LILO_RESUMO", "0")
    fake = FakeOllama([])  # qualquer chamada estouraria a fila
    podado = agente.ajustar_janela(_historico_grande(),
                                   cliente=ClienteOllama(transport=fake))
    assert not fake.chamadas
    corpo = " ".join(m.get("content") or "" for m in podado)
    assert agente.RESUMO_MARCA not in corpo
    orcamento = config.num_ctx() - config.max_tokens() - 1024
    assert sum(agente._tok(m) for m in podado) <= orcamento


def test_resumo_falho_cai_na_poda(monkeypatch):
    monkeypatch.setenv("LILO_NUM_CTX", "2048")
    monkeypatch.setenv("LILO_MAX_TOKENS", "256")
    import requests
    fake = FakeOllama([requests.ConnectionError(), requests.ConnectionError(),
                       requests.ConnectionError()])  # resumidor morre
    podado = agente.ajustar_janela(_historico_grande(),
                                   cliente=ClienteOllama(transport=fake))
    orcamento = config.num_ctx() - config.max_tokens() - 1024
    assert sum(agente._tok(m) for m in podado) <= orcamento  # poda segurou
