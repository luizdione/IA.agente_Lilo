"""
shared/obsidian.py — Integração LILO + Obsidian
=================================================
Salva execuções do LILO como notas no vault Obsidian com:
  - YAML frontmatter (pesquisável)
  - Wikilinks entre execuções
  - Índice automático

Baseado em: osquestrador_ollama/villa_lobos/obsidian_integration.py
Adaptado para a arquitetura LILO (subagentes, tiers, custos).

Uso:
    from shared.obsidian import save_lilo_run
    save_lilo_run(
        query="buscar artigos sobre docking",
        subagent="scholar",
        result="Encontrados 5 artigos...",
        tier="ollama",
        model="llama3.1:8b",
    )
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import get_env
from .logger import get_logger

log = get_logger("Obsidian")

# Configuração via .env
OBSIDIAN_VAULT = get_env("OBSIDIAN_VAULT", "")
OBSIDIAN_FOLDER = get_env("OBSIDIAN_LILO_FOLDER", "LILO")


def _get_vault_folder() -> Optional[Path]:
    """Retorna a pasta LILO no vault Obsidian, ou None se não configurado."""
    if not OBSIDIAN_VAULT:
        return None
    folder = Path(OBSIDIAN_VAULT) / OBSIDIAN_FOLDER
    try:
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    except Exception as e:
        log.warning(f"Obsidian vault não acessível: {e}")
        return None


def _sanitize(text: str, max_len: int = 60) -> str:
    clean = re.sub(r'[<>:"/\\|?*\n\r]', "", text)
    clean = re.sub(r'\s+', " ", clean).strip()
    return clean[:max_len]


def _recent_notes(folder: Path, limit: int = 5) -> list[str]:
    notes = sorted(folder.glob("*.md"), key=os.path.getmtime, reverse=True)
    return [n.stem for n in notes[:limit] if n.stem != "00 - Índice LILO"]


def save_lilo_run(
    query: str,
    subagent: str,
    result: str,
    tier: str = "",
    model: str = "",
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    status: str = "completed",
) -> Optional[str]:
    """
    Salva uma execução LILO como nota Obsidian.
    Retorna o caminho da nota ou None se Obsidian não configurado.
    """
    folder = _get_vault_folder()
    if not folder:
        return None

    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    readable = now.strftime("%Y-%m-%d %H:%M")
    date_only = now.strftime("%Y-%m-%d")
    slug = _sanitize(query)
    filename = f"{ts} - {slug}.md"
    filepath = folder / filename
    title = f"{ts} - {slug}"

    emoji = {"completed": "✅", "partial": "⚠️", "failed": "❌"}.get(status, "🔄")

    # Wikilinks
    recent = _recent_notes(folder)
    wikilinks = [f"[[{t}]]" for t in recent]

    content = f"""---
title: "{slug}"
date: {date_only}
datetime: "{readable}"
subagent: {subagent}
tier: {tier}
model: {model}
cost_usd: {cost_usd:.4f}
duration_ms: {duration_ms}
status: {status}
tags: [lilo, {subagent}, tier/{tier}, status/{status}]
---

# {emoji} {slug}

> **Query:** {query}
> **Subagente:** {subagent} | **Tier:** {tier} | **Modelo:** {model}
> **Executado em:** {readable} | **Duração:** {duration_ms}ms | **Custo:** ${cost_usd:.4f}

---

## Resultado

{result[:3000]}

---

## Execuções Relacionadas

{chr(10).join("- " + w for w in wikilinks) if wikilinks else "_Nenhuma execução anterior._"}

---
*Gerado automaticamente pelo [[LILO]]*
"""

    try:
        filepath.write_text(content, encoding="utf-8")
        _update_index(folder, title, query, readable, emoji, subagent)
        log.info(f"Nota Obsidian salva: {filepath.name}")
        return str(filepath)
    except Exception as e:
        log.warning(f"Falha ao salvar nota Obsidian: {e}")
        return None


def _update_index(folder, title, query, dt, emoji, subagent):
    idx = folder / "00 - Índice LILO.md"
    if not idx.exists():
        idx.write_text(f"""---
title: "Índice LILO"
tags: [lilo, índice]
---

# LILO — Índice de Execuções

| Data/Hora | Status | Subagente | Query | Nota |
|-----------|--------|-----------|-------|------|
""", encoding="utf-8")

    row = f"| {dt} | {emoji} | {subagent} | {query[:50]} | [[{title}]] |\n"
    current = idx.read_text(encoding="utf-8")
    idx.write_text(current + row, encoding="utf-8")
