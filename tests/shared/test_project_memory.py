"""Testes do leitor de memória de projetos (shared/project_memory.py).

Hermético: monta uma raiz de projetos falsa em tmp_path (não toca nos projetos
reais do dono) e valida list/read/digest/find.
"""
from __future__ import annotations

from pathlib import Path

from shared.project_memory import (
    ProjectMemory,
    list_projects,
    read_project,
    scan_all,
    digest_for,
    find_project_for_path,
    read_full,
    index,
    search_memory,
)


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "Projetos"
    # projeto A: memória em .project-memory/ + NEXT_SESSION na raiz
    a = root / "genomas"
    (a / ".project-memory").mkdir(parents=True)
    (a / ".project-memory" / "PROJECT_STATE.md").write_text(
        "# Estado\nssGBLUP rodando; falta validar herdabilidade.", encoding="utf-8")
    (a / ".project-memory" / "DECISIONS.md").write_text(
        "Usar BLUPF90.", encoding="utf-8")
    (a / "NEXT_SESSION.md").write_text(
        "Proxima: gerar figura Manhattan.", encoding="utf-8")
    # projeto B: só MEMORY.md na raiz
    b = root / "epigenoma"
    b.mkdir(parents=True)
    (b / "MEMORY.md").write_text("Metilação DMRs identificadas.", encoding="utf-8")
    # projeto C: sem memória nenhuma (não deve aparecer)
    (root / "sem_memoria").mkdir(parents=True)
    return root


def test_list_projects_so_com_memoria(tmp_path):
    root = _make_root(tmp_path)
    projs = list_projects(root=root)
    assert projs == ["epigenoma", "genomas"]  # ordenado; 'sem_memoria' excluído


def test_read_project_junta_subdir_e_raiz(tmp_path):
    root = _make_root(tmp_path)
    mem = read_project("genomas", root=root)
    assert isinstance(mem, ProjectMemory)
    assert mem.has_memory
    # pegou os 2 de .project-memory/ + o NEXT_SESSION.md da raiz
    assert set(mem.files) == {"PROJECT_STATE.md", "DECISIONS.md", "NEXT_SESSION.md"}
    assert "ssGBLUP" in mem.get("PROJECT_STATE.md")


def test_digest_prioriza_state_e_next(tmp_path):
    root = _make_root(tmp_path)
    d = digest_for("genomas", root=root)
    # prioritários aparecem com cabeçalho; DECISIONS vira "outros"
    assert "### PROJECT_STATE.md" in d
    assert "### NEXT_SESSION.md" in d
    assert "Manhattan" in d
    assert "outros arquivos de memória" in d and "DECISIONS.md" in d


def test_digest_trunca_no_budget(tmp_path):
    root = _make_root(tmp_path)
    big = root / "grande"
    (big / ".project-memory").mkdir(parents=True)
    (big / ".project-memory" / "PROJECT_STATE.md").write_text("x" * 9000, encoding="utf-8")
    d = digest_for("grande", root=root, max_chars=500)
    assert "[truncado]" in d
    assert len(d) < 2000


def test_scan_all(tmp_path):
    root = _make_root(tmp_path)
    idx = scan_all(root=root)
    assert set(idx) == {"epigenoma", "genomas"}
    assert idx["epigenoma"].get("MEMORY.md").startswith("Metilação")


def test_find_project_for_path(tmp_path):
    root = _make_root(tmp_path)
    p = root / "genomas" / "scripts" / "run.py"
    assert find_project_for_path(p, root=root) == "genomas"
    # caminho fora da raiz -> None
    assert find_project_for_path(tmp_path / "outro" / "x.py", root=root) is None


def test_projeto_sem_memoria(tmp_path):
    root = _make_root(tmp_path)
    mem = read_project("sem_memoria", root=root)
    assert not mem.has_memory
    assert "sem memória" in mem.digest()


def test_read_full_traz_tudo(tmp_path):
    root = _make_root(tmp_path)
    full = read_full("genomas", root=root)
    # 100%: contém os 3 arquivos, sem truncar
    assert "ssGBLUP" in full and "BLUPF90" in full and "Manhattan" in full
    assert "### PROJECT_STATE.md" in full and "### DECISIONS.md" in full


def test_index_lista_projetos_com_arquivos(tmp_path):
    root = _make_root(tmp_path)
    idx = index(root=root)
    slugs = {e["project"] for e in idx}
    assert slugs == {"epigenoma", "genomas"}
    g = next(e for e in idx if e["project"] == "genomas")
    assert g["n_files"] == 3 and "PROJECT_STATE.md" in g["files"]


def test_search_memory_encontra(tmp_path):
    root = _make_root(tmp_path)
    hits = search_memory("Manhattan", root=root)
    assert hits and hits[0]["project"] == "genomas"
    assert hits[0]["file"] == "NEXT_SESSION.md"
    # busca filtrada por projeto
    assert search_memory("Metilação", project="epigenoma", root=root)
    # termo inexistente
    assert search_memory("xyzabc123", root=root) == []
