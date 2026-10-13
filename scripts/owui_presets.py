"""Presets do LILO na Open WebUI, pela API. Idempotente: rode quantas vezes quiser.

    python scripts\\owui_presets.py            # cria ou atualiza os presets
    python scripts\\owui_presets.py --listar   # o que a interface expoe hoje

Sem login (D-0015): o token vem de /api/v1/auths/signin sem senha. Preset e um
registro de modelo no volume da interface (sobrevive a restart); a configuracao
em si (lista de modelos, geracoes de fundo, think:false) vive no compose.yaml.

Seletor ENXUTO (D-0022, 2026-10-12: o autor se perdeu em ~20 entradas). So cinco presets:
  LILO                        o proprio `lilo:latest` renomeado, com as tools locais (age por padrao).
  LILO Pesquisa               sobre o `lilo`: biblioteca, memoria, literatura (internet). Nao executa.
  LILO Desktop                sobre o `lilo`: Desktop Commander (arquivos e processos do Windows).
  LILO Orquestrador (Claude)  Sonnet 5.5 + tools locais: planeja e executa em etapas.
  LILO Pesquisa (Claude)      Sonnet 5.5 + literatura + MCPs bio (PubMed, bioRxiv, ChEMBL...).
Tudo o mais fica fora do seletor: modelos crus saem pela whitelist do compose.yaml e a base do
Claude por um registro inativo (OCULTOS). Bases hibridas (lilo-30b/32b/oss) e lilo-gemma continuam
no Ollama para medicao; uma base nova ("LILO Forte") so entra se passar no bench.
Regra mantida: conteudo da internet nunca fica no mesmo preset que executa codigo.
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
AGENTE = ["server:mcp:analise", "server:mcp:exec", "server:mcp:conhecimento"]   # age no host, sem internet

TOOLS: dict[str, list[str]] = {
    # 2026-10-12 (queixa do autor: "LILO 32B disse que nao pode executar nada"): TODO preset local
    # age por padrao - mesmas tools do Analise. Sem tool o modelo so pode dizer que nao consegue.
    # O "Modo de agir" (filtro) restringe quando o dono quiser; Pesquisa e o unico com internet.
    "lilo:latest": AGENTE,
    "lilo-pesquisa": ["server:mcp:conhecimento", "server:mcp:literatura"],
    # Servidor OpenAPI (mcpo) e `server:<id>`, sem o `mcp:`; as tools viram `tool_<nome>_post`.
    "lilo-desktop": ["server:desktop", "server:mcp:conhecimento"],
    # MCPs remotos dos plugins bio-research do Claude (PubMed, bioRxiv, ChEMBL, ensaios clinicos,
    # Open Targets) so no Claude: no `lilo` um preset com 3 deles media TTFT p50 3,7 s (schemas de
    # 4.098 tokens buscados nos servidores remotos a cada mensagem) e reprovou no bench de 12/10.
    # Orquestrador na nuvem (Claude Sonnet 5.5 pela API da Anthropic): mesmas tools do Analise.
    # Regra mantida: conteudo da internet nunca no mesmo preset que executa codigo.
    "lilo-orquestrador": ["server:mcp:conhecimento", "server:mcp:analise", "server:mcp:exec"],
    # Pesquisa com o Claude: biblioteca + literatura + os MCPs bio dos plugins (contexto de 200k).
    "lilo-pesquisa-claude": ["server:mcp:conhecimento", "server:mcp:literatura", "server:mcp:pubmed",
                             "server:mcp:biorxiv", "server:mcp:chembl", "server:mcp:ensaios",
                             "server:mcp:opentargets"],
}

# Presets que ja existiram e devem sumir da interface (apagados a cada rodada, se existirem).
OBSOLETOS = (
    "lilo-bio",          # reprovou no bench de 12/10 (TTFT p50 3,7 s com 3 MCPs remotos)
    "lilo-analise",      # D-0022: o LILO ja tem as mesmas tools (D-0021); preset redundante
    "lilo-gemma:latest", "lilo-30b:latest", "lilo-32b:latest", "lilo-oss:latest",   # D-0022: fora do seletor
)

# Bases que os presets usam mas que NAO devem aparecer soltas no seletor: registro inativo sobre o
# proprio id (e o que o "olho" do painel de administracao faz; utils/models.py remove o base da
# lista quando is_active e falso, mas o preset que o tem como base_model_id continua funcionando).
OCULTOS = ("claude-sonnet-5-5",)

PRESETS_SYSTEM_PT = ("Você é o LILO, assistente local de pesquisa de Luiz Dione. Responda sempre em "
                     "português do Brasil, mesmo que a pergunta ou o material estejam em inglês, de forma "
                     "direta e tecnicamente correta. Quando não souber, diga isso em vez de inventar.")

# System de quem AGE: o modelo tem ferramentas e deve usa-las em vez de dizer que nao consegue.
SYSTEM_AGENTE = (PRESETS_SYSTEM_PT +
                 " Você TEM ferramentas e deve usá-las: executar_python, executar_r e executar_wsl rodam "
                 "código no computador do dono; executar_git age nos repositórios de C:\\GitHub (status, log, "
                 "diff antes de alterar; commit só com o ok dele); pasta_escolher abre o seletor de pasta, "
                 "pasta_listar/pasta_buscar/ler_texto leem pastas e arquivos; biblioteca_buscar consulta os "
                 "PDFs; estat_* faz estatística; skills_listar -> skill_ler -> skill_rodar seguem as skills "
                 "do dono. Quando ele pedir uma tarefa, execute-a passo a passo com as ferramentas, mostrando "
                 "cada comando e saída tal como vieram; nunca responda que não pode acessar arquivos ou rodar "
                 "código. Só o que exige internet está fora deste preset (use o LILO Pesquisa).")

PRESETS = (
    {
        "id": "lilo:latest", "base_model_id": None, "name": "LILO",
        "meta": {"description": "qwen3:14b, contexto 8192, rápido. Age no computador: Python, R, WSL, git, "
                                "pastas, PDFs, estatística e skills. Para pensar, ligue 'Pensar fundo'.",
                 "tags": [{"name": "local"}]},
        # O SYSTEM do Modelfile ja pede portugues; o preset repete porque, na interface, um
        # system do preset substitui o do modelo (e o dono quer PT sempre, mesmo com material em ingles).
        "params": {"system": SYSTEM_AGENTE},
    },
    # Bases hibridas (lilo-30b/32b/oss) e lilo-gemma sairam do seletor em 12/10 (D-0022): medidas,
    # nenhuma passou no portao; continuam no Ollama. "LILO Forte" (qwen3:30b-a3b-instruct-2507, em
    # Modelfile.lilo-30b) entra aqui, com AGENTE e na whitelist do compose, so se passar no bench.
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
        "id": "lilo-desktop", "base_model_id": "lilo:latest", "name": "LILO Desktop",
        "meta": {"description": "Desktop Commander: arquivos, pastas, busca, processos e PowerShell "
                                "no computador do dono. Sem internet.",
                 "tags": [{"name": "local"}, {"name": "desktop"}]},
        "params": {"system": "Você é o LILO em modo Desktop e tem acesso ao computador do dono pelas "
                             "ferramentas do Desktop Commander (tool_*): tool_list_directory_post, "
                             "tool_read_file_post, tool_write_file_post, tool_edit_block_post, "
                             "tool_start_search_post, tool_start_process_post (PowerShell) e "
                             "tool_read_process_output_post. Responda sempre em português do Brasil. "
                             "Pasta ou arquivo citado pelo dono: use o caminho exatamente como ele deu. "
                             "Antes de criar, alterar ou mover qualquer coisa, diga o que vai fazer; "
                             "mostre comandos e saídas tal como vieram. Para memória dos projetos, PDFs e "
                             "skills do dono use as ferramentas de conhecimento. Não invente caminhos."},
    },
    {
        "id": "lilo-orquestrador", "base_model_id": "claude-sonnet-5-5", "name": "LILO Orquestrador (Claude)",
        "meta": {"description": "Claude Sonnet 5.5 pela API da Anthropic com as ferramentas da ponte "
                                "(memória, biblioteca, skills, estatística, Python/R/WSL, git). Para "
                                "tarefas longas e em etapas. Custa tokens.",
                 "tags": [{"name": "nuvem"}, {"name": "orquestrador"}]},
        "params": {"system": "Você é o LILO Orquestrador: planeja e executa tarefas em etapas no computador "
                             "do dono usando as ferramentas disponíveis (memória dos projetos, biblioteca de "
                             "PDFs, skills, pastas, repositórios git, estatística, Python, R e WSL). Responda "
                             "sempre em português do Brasil. Comece com um plano curto, execute passo a passo, "
                             "mostre comandos e saídas tal como vieram e feche com o que foi feito e o que "
                             "falta. Skills do dono: skills_listar -> skill_ler (siga o SKILL.md) -> "
                             "skill_rodar. Commit só com o ok dele. Não invente números nem caminhos."},
    },
    {
        "id": "lilo-pesquisa-claude", "base_model_id": "claude-sonnet-5-5", "name": "LILO Pesquisa (Claude)",
        "meta": {"description": "Claude Sonnet 5.5 com biblioteca de PDFs, literatura (paper-search), "
                                "PubMed, bioRxiv, ChEMBL, ensaios clínicos e Open Targets. Sem execução. "
                                "Custa tokens.",
                 "tags": [{"name": "nuvem"}, {"name": "pesquisa"}]},
        "params": {"system": "Você é o LILO em modo Pesquisa com o Claude. Responda sempre em português do "
                             "Brasil. Para fontes use biblioteca_buscar (PDFs do dono) e as ferramentas de "
                             "literatura e dos bancos biomédicos; cite título, autores, ano e identificador "
                             "(PMID, DOI, ChEMBL ID, NCT). Se não encontrar, diga; não invente referências."},
    },
)

# Atalhos da caixa de mensagem (Workspace > Prompts): o dono digita /pasta, /repo ou /skill e
# preenche o que esta entre colchetes. E o "anexar pasta" possivel na Open WebUI: nao ha
# upload de diretorio no chat, e como o LILO roda no host, citar o caminho basta.
PROMPTS = (
    # "Anexar pasta": /pasta faz o modelo abrir o seletor de pasta do Windows (tool pasta_escolher,
    # na tela do dono); /pasta_colada usa o caminho copiado no Explorer (Ctrl+Shift+C -> {{CLIPBOARD}}).
    {"command": "/pasta", "name": "Escolher pasta (abre o seletor do Windows)",
     "content": "Abra o seletor de pasta com pasta_escolher e trabalhe na pasta escolhida: liste-a com "
                "pasta_listar, leia com ler_texto o que for relevante para [o que eu quero] e me diga o "
                "que encontrou antes de agir."},
    {"command": "/pasta_colada", "name": "Pasta colada (copie o caminho no Explorer e digite /pasta_colada)",
     "content": "Trabalhe na pasta {{CLIPBOARD}}: liste-a com pasta_listar, leia com ler_texto "
                "o que for relevante para [o que eu quero] e me diga o que encontrou antes de agir."},
    {"command": "/repo", "name": "Trabalhar num repositorio do GitHub",
     "content": "Trabalhe no repositório [nome da pasta em C:\\GitHub]: use repos_listar e executar_git "
                "(status, log -5, diff) para me situar e depois [o que eu quero]. Só altere ou faça "
                "commit depois do meu ok."},
    {"command": "/skill", "name": "Usar uma skill do dono",
     "content": "Use a skill [nome da skill] para [o que eu quero]: leia-a com skill_ler, siga as "
                "instruções e rode os scripts dela com skill_rodar, mostrando cada saída."},
)


MARCA_SKILL = "Skill: "   # prefixo do nome = prompt gerado daqui (e o que a poda reconhece)


def prompts_das_skills() -> list[dict]:
    """Um comando `/<skill>` por skill propria (como no Claude Code) + as do plugin `bioinfo`
    + `/bioinfo` para as 815 da biblioteca (sao demais para o menu). Lidos do catalogo da
    ponte, no lugar. Skills de plugins alheios (ory-*, doctor, reindex...) ficam de fora."""
    import re
    import sys
    sys.path.insert(0, str(ROOT))
    try:
        from lilo_host import skills
    except ImportError:
        return []
    out = []
    for it in skills.catalogo().values():
        pasta = it["pasta_nome"].lower()
        if not (it["origem"] == "skills" or (it["origem"] == "plugins" and pasta.startswith("bioinfo"))):
            continue
        cmd = "/" + re.sub(r"[^a-z0-9_-]", "_", pasta)
        if cmd == "/bioinfo":           # o roteador do plugin: coberto pelo /bioinfo fixo abaixo
            continue
        desc = (it["descricao"][:140] + "...") if len(it["descricao"]) > 140 else it["descricao"]
        out.append({"command": cmd, "name": MARCA_SKILL + it["nome"],
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
    desejados = list(PROMPTS) + prompts_das_skills()
    for p in desejados:
        form = {"command": p["command"], "name": p["name"], "content": p["content"]}
        if p["command"] in existentes:
            r = cli.post(f"{BASE}/api/v1/prompts/id/{existentes[p['command']]['id']}/update", json=form)
            acao = "atualizado"
        else:
            r = cli.post(f"{BASE}/api/v1/prompts/create", json=form)
            acao = "criado"
        print(f"  {p['command']:<14} {acao if r.status_code == 200 else '%d %s' % (r.status_code, r.text[:120])}")
    # Poda: so o que este script gerou (nome "Skill: ...") e que deixou de existir ou de ser
    # desejado. Prompts criados a mao na interface nao tem a marca e ficam.
    manter = {p["command"] for p in desejados}
    for cmd, p in existentes.items():
        if cmd not in manter and str(p.get("name", "")).startswith(MARCA_SKILL):
            r = cli.delete(f"{BASE}/api/v1/prompts/id/{p['id']}/delete")
            print(f"  {cmd:<14} {'removido' if r.status_code == 200 else '%d %s' % (r.status_code, r.text[:120])}")


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


def ocultar(cli: httpx.Client, id_: str) -> str:
    """Registro inativo sobre o proprio id do modelo base (OCULTOS): some do seletor, continua
    servindo os presets que o tem como base_model_id."""
    form = {"id": id_, "base_model_id": None, "name": id_, "meta": {}, "params": {}, "is_active": False}
    if existe(cli, id_):
        r = cli.post(f"{BASE}/api/v1/models/model/update", params={"id": id_}, json=form)
    else:
        r = cli.post(f"{BASE}/api/v1/models/create", json=form)
    return "oculto" if r.status_code == 200 else f"{r.status_code} {r.text[:120]}"


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
        for id_ in OCULTOS:
            print(f"  {id_:<14} {ocultar(cli, id_)}")
        for id_ in OBSOLETOS:
            if existe(cli, id_):
                r = cli.post(f"{BASE}/api/v1/models/model/delete", json={"id": id_})  # POST com corpo
                print(f"  {id_:<14} {'removido' if r.status_code == 200 else '%d %s' % (r.status_code, r.text[:120])}")
        aplicar_prompts(cli)
        listar(cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
