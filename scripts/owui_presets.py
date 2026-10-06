"""Presets do LILO na Open WebUI, pela API. Idempotente: rode quantas vezes quiser.

    python scripts\\owui_presets.py            # cria ou atualiza os presets
    python scripts\\owui_presets.py --listar   # o que a interface expoe hoje

Sem login (D-0015): o token vem de /api/v1/auths/signin sem senha. Preset e um
registro de modelo no volume da interface (sobrevive a restart); a configuracao
em si (lista de modelos, geracoes de fundo, think:false) vive no compose.yaml.

Presets do plano v14:
  LILO           o proprio `lilo:latest`, so renomeado. Sem tools, sem thinking:
                 e o caminho do "2+2".
  LILO Pesquisa  `lilo-pesquisa` sobre o `lilo`: biblioteca, memoria dos projetos,
                 literatura e busca web (tools ligadas na F2 e na F4).
  LILO Analise   `lilo-analise` sobre o `lilo`: estatistica, parsers bio, Python,
                 R e WSL no host; SEM web (tools ligadas na F2). Conteudo da
                 internet nunca fica no mesmo preset que executa codigo.
As tools entram aqui, em TOOLS, quando a ponte lilo-host existir.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("LILO_WEBUI", "http://127.0.0.1:3000")

# Tools por preset: `server:mcp:<id>` = conexao MCP de TOOL_SERVER_CONNECTIONS
# (compose.yaml); a Open WebUI expoe cada tool como `<id>_<nome>`. A F4 acrescenta
# o paper-search ao Pesquisa. Conteudo da internet nunca no mesmo preset que executa.
TOOLS: dict[str, list[str]] = {
    "lilo-pesquisa": ["server:mcp:conhecimento", "server:mcp:literatura"],
    "lilo-analise": ["server:mcp:analise", "server:mcp:exec", "server:mcp:conhecimento"],
}

PRESETS = (
    {
        "id": "lilo:latest", "base_model_id": None, "name": "LILO",
        "meta": {"description": "Chat rápido local (qwen3:14b, contexto 8192, sem thinking). "
                                "Para raciocínio profundo, ligue o thinking na conversa.",
                 "tags": [{"name": "local"}]},
        # O SYSTEM do Modelfile ja pede portugues; o preset repete porque, na interface, um
        # system do preset substitui o do modelo (e o dono quer PT sempre, mesmo com material em ingles).
        "params": {"system": "Você é o LILO, assistente local de pesquisa de Luiz Dione. Responda "
                             "sempre em português do Brasil, mesmo que a pergunta ou o material estejam "
                             "em inglês, de forma direta e tecnicamente correta. Quando não souber, "
                             "diga isso em vez de inventar."},
    },
    {
        "id": "lilo-pesquisa", "base_model_id": "lilo:latest", "name": "LILO Pesquisa",
        "meta": {"description": "Biblioteca de PDFs, memória dos projetos, literatura "
                                "(PubMed etc.) e busca web.",
                 "tags": [{"name": "local"}, {"name": "pesquisa"}]},
        "params": {"system": "Você é o LILO em modo Pesquisa. Responda sempre em português do Brasil, "
                             "mesmo que a pergunta ou o material estejam em inglês. Quando a "
                             "pergunta pedir fontes, use biblioteca_buscar (PDFs do dono) e as "
                             "ferramentas de literatura e cite o que encontrar (título, autores, ano, "
                             "página). Se o dono citar uma pasta ou arquivo, use pasta_listar, "
                             "pasta_buscar e ler_texto. Se o pedido casar com uma skill do dono "
                             "(skills_listar), leia-a com skill_ler e siga as instruções dela. Se não "
                             "encontrar, diga que não encontrou; não invente referências."},
    },
    {
        "id": "lilo-analise", "base_model_id": "lilo:latest", "name": "LILO Análise",
        "meta": {"description": "Estatística, parsers bio e execução de Python, R e WSL no "
                                "host. Sem internet.",
                 "tags": [{"name": "local"}, {"name": "analise"}]},
        "params": {"system": "Você é o LILO em modo Análise. Responda sempre em português do Brasil, "
                             "mesmo que o material esteja em inglês. Para contas, "
                             "estatística e arquivos use as ferramentas de análise e execução; "
                             "mostre o código ou comando que rodou e o resultado tal como veio. "
                             "Pasta citada pelo dono: pasta_listar, pasta_buscar, ler_texto; "
                             "repositório em C:\\GitHub: repos_listar e executar_git (status, log, "
                             "diff antes de qualquer alteração; commit só com o ok dele). Skills do "
                             "dono: skills_listar -> skill_ler (siga o SKILL.md como roteiro) -> "
                             "skill_rodar para os scripts dela. Não invente números."},
    },
)

# Atalhos da caixa de mensagem (Workspace > Prompts): o dono digita /pasta, /repo ou /skill e
# preenche o que esta entre colchetes. E o "anexar pasta" possivel na Open WebUI: nao ha
# upload de diretorio no chat, e como o LILO roda no host, citar o caminho basta.
PROMPTS = (
    {"command": "/pasta", "name": "Trabalhar numa pasta",
     "content": "Trabalhe na pasta [caminho da pasta]: liste-a com pasta_listar, leia com ler_texto "
                "o que for relevante para [o que eu quero] e me diga o que encontrou antes de agir."},
    {"command": "/repo", "name": "Trabalhar num repositorio do GitHub",
     "content": "Trabalhe no repositório [nome da pasta em C:\\GitHub]: use repos_listar e executar_git "
                "(status, log -5, diff) para me situar e depois [o que eu quero]. Só altere ou faça "
                "commit depois do meu ok."},
    {"command": "/skill", "name": "Usar uma skill do dono",
     "content": "Use a skill [nome da skill] para [o que eu quero]: leia-a com skill_ler, siga as "
                "instruções e rode os scripts dela com skill_rodar, mostrando cada saída."},
)


def prompts_das_skills() -> list[dict]:
    """Um comando `/<skill>` por skill propria ou de plugin (como no Claude Code) + `/bioinfo`
    para as 815 da biblioteca (sao demais para o menu). Lidos do catalogo da ponte, no lugar."""
    import re
    import sys
    sys.path.insert(0, str(ROOT))
    try:
        from lilo_host import skills
    except ImportError:
        return []
    out = []
    for it in skills.catalogo().values():
        if it["origem"] not in ("skills", "plugins"):
            continue
        cmd = "/" + re.sub(r"[^a-z0-9_-]", "_", it["pasta_nome"].lower())
        desc = (it["descricao"][:140] + "...") if len(it["descricao"]) > 140 else it["descricao"]
        out.append({"command": cmd, "name": "Skill: %s" % it["nome"],
                    "content": "Use a skill %s (%s) para: [o que eu quero]. Leia-a com skill_ler, siga as "
                               "instruções dela e, se houver scripts, rode-os com skill_rodar mostrando cada "
                               "saída. Responda em português." % (it["nome"], desc)})
    out.append({"command": "/bioinfo", "name": "Skill de bioinformatica (815 na biblioteca)",
                "content": "Tarefa de bioinformática: [o que eu quero]. Procure a skill certa com "
                           "skills_listar usando as palavras-chave da tarefa, leia a melhor com skill_ler "
                           "e siga o roteiro dela; rode scripts com skill_rodar. Responda em português."})
    return out


def aplicar_prompts(cli: httpx.Client) -> None:
    r = cli.get(f"{BASE}/api/v1/prompts/")
    r.raise_for_status()
    existentes = {p["command"]: p for p in r.json()}
    for p in list(PROMPTS) + prompts_das_skills():
        form = {"command": p["command"], "name": p["name"], "content": p["content"]}
        if p["command"] in existentes:
            r = cli.post(f"{BASE}/api/v1/prompts/id/{existentes[p['command']]['id']}/update", json=form)
            acao = "atualizado"
        else:
            r = cli.post(f"{BASE}/api/v1/prompts/create", json=form)
            acao = "criado"
        print(f"  {p['command']:<14} {acao if r.status_code == 200 else '%d %s' % (r.status_code, r.text[:120])}")


def token(cli: httpx.Client) -> str:
    r = cli.post(f"{BASE}/api/v1/auths/signin", json={"email": "", "password": ""})
    if r.status_code != 200:
        sys.exit(f"signin sem senha falhou ({r.status_code}): a interface esta com login? "
                 "O compose roda com WEBUI_AUTH=False (D-0015).")
    cli.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return r.json()["token"]


def existe(cli: httpx.Client, id_: str) -> bool:
    r = cli.get(f"{BASE}/api/v1/models/model", params={"id": id_})
    return r.status_code == 200 and bool(r.json())


def aplicar(cli: httpx.Client, preset: dict) -> str:
    meta = dict(preset["meta"])
    if preset["id"] in TOOLS:
        meta["toolIds"] = TOOLS[preset["id"]]
    form = {"id": preset["id"], "base_model_id": preset["base_model_id"],
            "name": preset["name"], "meta": meta, "params": preset["params"],
            "is_active": True}
    if existe(cli, preset["id"]):
        r = cli.post(f"{BASE}/api/v1/models/model/update", params={"id": preset["id"]}, json=form)
        acao = "atualizado"
    else:
        r = cli.post(f"{BASE}/api/v1/models/create", json=form)
        acao = "criado"
    if r.status_code != 200:
        sys.exit(f"{preset['id']}: {r.status_code} {r.text[:300]}")
    return acao


def listar(cli: httpx.Client) -> None:
    r = cli.get(f"{BASE}/api/models")
    r.raise_for_status()
    print("Modelos que a interface expoe:")
    for m in r.json().get("data", []):
        info = m.get("info") or {}
        base = info.get("base_model_id")
        print(f"  {m['id']:<30} {m.get('name', ''):<16}" + (f" (sobre {base})" if base else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    with httpx.Client(timeout=60) as cli:
        try:
            token(cli)
        except httpx.ConnectError:
            sys.exit(f"Interface fora do ar em {BASE}. Suba com:  .\\lilo.ps1 up")
        if a.listar:
            listar(cli)
            return 0
        for p in PRESETS:
            print(f"  {p['name']:<14} {aplicar(cli, p)}")
        aplicar_prompts(cli)
        listar(cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
