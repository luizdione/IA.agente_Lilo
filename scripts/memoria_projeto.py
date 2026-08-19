"""scripts/memoria_projeto.py — V18.10: gerente de memoria do projeto.

Regenera as secoes AUTO do CONTEXT.md (raiz do repo) com 0 tokens de LLM:
versao (badge do README), branch/commit (git), contagem de testes, resumo do
/diagnostico_lilo e ultimas entregas (topo do CHANGELOG). As secoes MANUAL
(pendencias, decisoes, como retomar) sao preservadas byte a byte — o script
so toca o que esta entre marcadores <!-- AUTO:x --> ... <!-- /AUTO:x -->.

Por que existe: o CONTEXT.md e lido automaticamente pelo LILO (dir_synthesis,
E4) e pelo Claude Code no inicio de sessao — manter esse arquivo fresco faz
qualquer sessao retomar o projeto sem re-explorar o repositorio (economia de
tokens). Skill correspondente: /gerente_memoria.

Uso:
    python scripts/memoria_projeto.py            # atualiza CONTEXT.md
    python scripts/memoria_projeto.py --no-diag  # pula o diagnostico (rapido)
    python scripts/memoria_projeto.py --print    # tambem imprime o resultado
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "CONTEXT.md"
CHANGELOG = ROOT / "docs" / "versoes" / "CHANGELOG.md"

# Template usado so quando o CONTEXT.md ainda nao existe. As secoes MANUAL
# vem vazias de proposito: quem preenche e o dono (ou a sessao, a pedido).
TEMPLATE = """# CONTEXT.md — memoria do projeto LILO

> Secoes **AUTO** sao regeneradas por `python scripts/memoria_projeto.py`
> (skill `/gerente_memoria`) — NAO edite dentro dos marcadores. Secoes
> **MANUAL** sao suas: mantenha-as curtas (isto entra no contexto de
> sessoes do LILO e do Claude Code).

## Estado atual (AUTO)
<!-- AUTO:estado -->
<!-- /AUTO:estado -->

## Ultimas entregas (AUTO — topo do CHANGELOG)
<!-- AUTO:entregas -->
<!-- /AUTO:entregas -->

## Pendencias (MANUAL)

(vazio)

## Decisoes-chave (MANUAL)

(vazio)

## Como retomar uma sessao (MANUAL)

```cmd
python scripts\\check.py                          # saude do codigo
python scripts\\diagnostico_lilo.py --fast        # auditoria compacta
python scripts\\memoria_projeto.py                # atualiza esta memoria
streamlit run dashboard.py                        # UI -> localhost:8100
```
"""


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _versao() -> str:
    try:
        m = re.search(r"badge/version-([\d.]+)-",
                      (ROOT / "README.md").read_text(encoding="utf-8"))
        return m.group(1) if m else "?"
    except Exception:
        return "?"


def _n_testes() -> int:
    n = 0
    for p in (ROOT / "tests").rglob("test_*.py"):
        try:
            n += len(re.findall(r"^def test_", p.read_text(encoding="utf-8"),
                                re.MULTILINE))
        except Exception:
            pass
    return n


def _diag_resumo() -> str:
    """Roda o diagnostico rapido e devolve so a linha de resumo."""
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "diagnostico_lilo.py"),
             "--fast", "--no-runtime"],
            cwd=ROOT, capture_output=True, text=True, timeout=180)
        m = re.search(r"\*\*Resumo:\*\*\s*(.+)", r.stdout)
        return m.group(1).strip() if m else "(sem resumo)"
    except Exception as e:
        return "(diagnostico indisponivel: %s)" % e


def _estado_md(run_diag: bool = True) -> str:
    linhas = [
        "- **Versao:** v%s | **branch:** %s | **commit:** %s" % (
            _versao(), _git("branch", "--show-current") or "?",
            _git("log", "-1", "--format=%h %s") or "?"),
        "- **Testes:** %d funcoes de teste (rode `python scripts/check.py`)"
        % _n_testes(),
    ]
    if run_diag:
        linhas.append("- **Diagnostico:** %s" % _diag_resumo())
    linhas.append("- **Atualizado em:** %s" % date.today().isoformat())
    return "\n".join(linhas)


def _entregas_md(max_itens: int = 3) -> str:
    try:
        txt = CHANGELOG.read_text(encoding="utf-8")
    except Exception:
        return "(CHANGELOG indisponivel)"
    heads = re.findall(r"^## (v[\d.]+ — .+)$", txt, re.MULTILINE)
    if not heads:
        return "(CHANGELOG sem entradas)"
    return "\n".join("- %s" % h for h in heads[:max_itens])


def _substitui_bloco(texto: str, nome: str, conteudo: str) -> str:
    ini, fim = "<!-- AUTO:%s -->" % nome, "<!-- /AUTO:%s -->" % nome
    if ini not in texto or fim not in texto:
        raise ValueError("marcadores AUTO:%s ausentes no CONTEXT.md" % nome)
    antes = texto.split(ini)[0]
    depois = texto.split(fim)[1]
    return antes + ini + "\n" + conteudo + "\n" + fim + depois


def refresh(path: Path = CONTEXT, run_diag: bool = True) -> str:
    """Atualiza (ou cria) o CONTEXT.md e devolve o texto final."""
    texto = path.read_text(encoding="utf-8") if path.exists() else TEMPLATE
    texto = _substitui_bloco(texto, "estado", _estado_md(run_diag))
    texto = _substitui_bloco(texto, "entregas", _entregas_md())
    path.write_text(texto, encoding="utf-8")
    return texto


def main() -> int:
    run_diag = "--no-diag" not in sys.argv
    novo = not CONTEXT.exists()
    texto = refresh(run_diag=run_diag)
    print("CONTEXT.md %s (%d linhas)%s" % (
        "criado" if novo else "atualizado", texto.count("\n") + 1,
        "" if run_diag else " [--no-diag]"))
    if "--print" in sys.argv:
        print("\n" + texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
