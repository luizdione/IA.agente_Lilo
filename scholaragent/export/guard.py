"""
export/guard.py — O export só aceita conteúdo verificado E aprovado por humano.
É a aplicação da "regra de ouro": o gate nunca auto-publica.
"""
from __future__ import annotations
from ..verify.contracts import GateReport, Decision


class ExportBlocked(Exception):
    """Levantada quando se tenta exportar conteúdo não liberado pelo gate."""


def can_export(report: GateReport) -> bool:
    """Libera export apenas se decision == PASS E houve aprovação humana."""
    return report.decision == Decision.PASS and report.human_approved


def assert_exportable(report: GateReport) -> None:
    if not can_export(report):
        raise ExportBlocked(
            f"Conteúdo {report.content_id} não liberado: "
            f"decision={report.decision.value}, human_approved={report.human_approved}"
        )
