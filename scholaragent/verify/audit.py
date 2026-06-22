"""
verify/audit.py — Trilha de auditoria em JSON (reprodutibilidade + disclosure de IA).

Permite declarar com honestidade: "rascunho assistido por LLM local, com verificação
factual automática contra a biblioteca e revisão humana — registro em audit/<id>.json".
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict

from .contracts import GateReport


def write_audit(report: GateReport, out_dir: str = "./audit") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / f"{report.content_id}.json"
    path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2, default=_enc),
        encoding="utf-8",
    )
    return str(path)


def _enc(o):
    """Enums viram seu valor; demais objetos não serializáveis viram str."""
    return getattr(o, "value", str(o))
