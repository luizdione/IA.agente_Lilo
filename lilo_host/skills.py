"""Skills do Claude Code lidas NO LUGAR (grupo conhecimento): catalogo das raizes do dono.

Raizes (LILO_SKILLS_RAIZES, separadas por `;`; padrao abaixo):
  ~/.claude/skills           skills proprias (build_paper, git_dione, perfil_dados...)
  ~/.claude/skills_bioinfo   815 skills de bioinformatica (<dominio>/<skill>/SKILL.md)
  ~/.claude/plugins          plugins (SKILL.md em qualquer profundidade)

Nada e copiado para o LILO: `ler` devolve o SKILL.md tal como esta (o modelo segue as
instrucoes como roteiro) e `script` resolve um arquivo DENTRO da pasta da skill para o
grupo exec rodar no env datascience. O catalogo (nome, descricao, origem, pasta) le so o
frontmatter de cada SKILL.md e fica em cache ate uma raiz mudar.
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path

CASA = Path.home() / ".claude"
RAIZES_PADRAO = {"skills": CASA / "skills", "skills_bioinfo": CASA / "skills_bioinfo",
                 "plugins": CASA / "plugins"}
PROFUNDIDADE = {"skills": 2, "skills_bioinfo": 3, "plugins": 9}
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "synced"}
LER_MAX = 40000
_cache: dict = {"em": 0.0, "assinatura": None, "itens": {}}


def raizes() -> dict[str, Path]:
    env = os.environ.get("LILO_SKILLS_RAIZES", "")
    if env:
        return {Path(p.strip()).name: Path(p.strip()) for p in env.split(";") if p.strip() and Path(p.strip()).is_dir()}
    return {k: v for k, v in RAIZES_PADRAO.items() if v.is_dir()}


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def frontmatter(texto: str) -> dict[str, str]:
    """Cabecalho YAML simples (name, description...) com valores dobrados (`>-`, `|`)."""
    linhas = texto.splitlines()
    if not linhas or linhas[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    chave = None
    for linha in linhas[1:]:
        if linha.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", linha)
        if m and not linha.startswith((" ", "\t")):
            chave, valor = m.group(1), m.group(2).strip()
            out[chave] = "" if valor in (">-", ">", "|", "|-") else valor.strip("'\"")
        elif chave and linha.startswith((" ", "\t")):
            out[chave] = (out[chave] + " " + linha.strip()).strip()
    return out


def _varrer(origem: str, raiz: Path) -> list[dict]:
    itens = []
    prof = PROFUNDIDADE.get(origem, 4)
    pilha = [(raiz, 0)]
    while pilha:
        d, nivel = pilha.pop()
        try:
            filhos = list(d.iterdir())
        except OSError:
            continue
        for f in filhos:
            if f.is_dir():
                if f.name in IGNORAR or f.name.startswith("."):
                    continue
                if nivel + 1 <= prof:
                    pilha.append((f, nivel + 1))
            elif f.name == "SKILL.md":
                try:
                    fm = frontmatter(f.read_text(encoding="utf-8", errors="replace")[:6000])
                except OSError:
                    continue
                rel = f.parent.relative_to(raiz)
                itens.append({"nome": fm.get("name") or f.parent.name, "pasta_nome": f.parent.name,
                              "descricao": fm.get("description", ""), "origem": origem,
                              "dominio": rel.parts[0] if len(rel.parts) > 1 else "",
                              "pasta": str(f.parent)})
    return itens


def catalogo(forcar: bool = False) -> dict[str, dict]:
    """{nome -> item}; refeito quando a assinatura (mtime das raizes) muda ou a cada 10 min."""
    rz = raizes()
    assinatura = tuple((k, int(p.stat().st_mtime)) for k, p in rz.items())
    if (not forcar and _cache["itens"] and _cache["assinatura"] == assinatura
            and time.time() - _cache["em"] < 600):
        return _cache["itens"]
    itens: dict[str, dict] = {}
    for origem, raiz in rz.items():
        for it in sorted(_varrer(origem, raiz), key=lambda x: x["pasta"]):
            nome = it["nome"]
            if nome in itens and itens[nome]["pasta"] != it["pasta"]:
                nome = "%s@%s" % (nome, origem)
            it["nome"] = nome
            itens[nome] = it
    _cache.update(em=time.time(), assinatura=assinatura, itens=itens)
    return itens


def listar(filtro: str = "", limite: int = 30) -> dict:
    """Skills que casam com `filtro` (nome, descricao ou dominio). Sem filtro: as proprias
    do dono por inteiro e so a contagem das outras raizes (sao centenas)."""
    cat = catalogo()
    contagem: dict[str, int] = {}
    for it in cat.values():
        contagem[it["origem"]] = contagem.get(it["origem"], 0) + 1
    q = _sem_acento(filtro.strip())
    if not q:
        proprias = [it for it in cat.values() if it["origem"] == "skills"]
        return {"contagem": contagem, "skills": [_resumo(it) for it in proprias],
                "dica": "passe um filtro (ex.: 'qpcr', 'docking', 'git') para ver as outras raizes"}
    termos = q.split()
    achados = []
    for it in cat.values():
        alvo = _sem_acento(" ".join((it["nome"], it["pasta_nome"], it["descricao"], it["dominio"])))
        if all(t in alvo for t in termos):
            achados.append(it)
    achados.sort(key=lambda it: (it["origem"] != "skills", q not in _sem_acento(it["nome"]), it["nome"]))
    return {"contagem": contagem, "total_casados": len(achados),
            "skills": [_resumo(it) for it in achados[:max(1, limite)]]}


def _resumo(it: dict) -> dict:
    d = it["descricao"]
    return {"nome": it["nome"], "origem": it["origem"], "dominio": it["dominio"],
            "descricao": d[:220] + ("..." if len(d) > 220 else "")}


def pasta(nome: str) -> Path | None:
    cat = catalogo()
    it = cat.get(nome) or next((x for x in cat.values() if x["pasta_nome"] == nome), None)
    return Path(it["pasta"]) if it else None


def ler(nome: str) -> str:
    """SKILL.md inteiro (ate 40k caracteres) + lista de arquivos da pasta."""
    p = pasta(nome)
    if p is None:
        return "[ERRO] skill '%s' nao encontrada; use skills_listar" % nome
    texto = (p / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if len(texto) > LER_MAX:
        texto = texto[:LER_MAX] + "\n...[truncado em %d caracteres]" % LER_MAX
    arquivos = []
    for f in sorted(p.rglob("*")):
        if f.is_file() and not any(part in IGNORAR for part in f.relative_to(p).parts):
            arquivos.append(f.relative_to(p).as_posix())
        if len(arquivos) >= 60:
            arquivos.append("...")
            break
    return "[skill %s em %s]\narquivos: %s\n\n%s" % (nome, p, ", ".join(arquivos), texto)


def script(nome: str, relativo: str) -> Path | str:
    """Caminho de um script DENTRO da pasta da skill (sem sair dela), ou mensagem de erro."""
    p = pasta(nome)
    if p is None:
        return "[ERRO] skill '%s' nao encontrada" % nome
    alvo = (p / relativo).resolve()
    try:
        alvo.relative_to(p.resolve())
    except ValueError:
        return "[ERRO] '%s' esta fora da pasta da skill" % relativo
    if not alvo.is_file():
        return "[ERRO] script '%s' nao existe na skill %s" % (relativo, nome)
    return alvo
