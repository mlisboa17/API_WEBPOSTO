"""F08.4 IA-5 — Receivables & Payables Intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.services.financial_intelligence_evidence import build_lineage, get_financial_intelligence_evidence
from src.services.financial_snapshot_config import get_financial_snapshot_config


class FinancialCommitmentsIntelligence:
    def __init__(self) -> None:
        self._evidence = get_financial_intelligence_evidence()

    def _resolve_period(
        self,
        data_inicial: str | None,
        data_final: str | None,
    ) -> tuple[str, str]:
        cfg = get_financial_snapshot_config()
        return data_inicial or cfg.default_period()[0], data_final or cfg.default_period()[1]

    def analyze(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        start, end = self._resolve_period(data_inicial, data_final)
        current = self._evidence.load_period(start, end, empresa_codigo)
        metrics = self._evidence.compute_metrics(current)

        rec_rows = ((current.receivables or {}).get("data") or {}).get("data") or []
        pay_rows = ((current.payables or {}).get("data") or {}).get("data") or []

        receivable_health = "SAUDÁVEL"
        if metrics.overdue_receivables > 0:
            receivable_health = "ATENÇÃO"
        if metrics.receivable_top_share >= 70:
            receivable_health = "CONCENTRADO"

        payable_health = "SAUDÁVEL"
        if metrics.overdue_payables > 0:
            payable_health = "ATENÇÃO"
        if metrics.pagamentos > metrics.recebimentos and metrics.recebimentos > 0:
            payable_health = "PRESSÃO"

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": start, "dataFinal": end},
            "empresaCodigo": empresa_codigo,
            "receivables": {
                "total": float(metrics.recebimentos),
                "rows": metrics.receivable_rows,
                "overdue": float(metrics.overdue_receivables),
                "concentrationTopSharePct": metrics.receivable_top_share,
                "health": receivable_health,
                "lineage": build_lineage("financial_receivables", current.receivables, metric="receivables"),
            },
            "payables": {
                "total": float(metrics.pagamentos),
                "rows": metrics.payable_rows,
                "overdue": float(metrics.overdue_payables),
                "health": payable_health,
                "lineage": build_lineage("financial_payables", current.payables, metric="payables"),
            },
            "delinquencyRelevant": metrics.overdue_receivables > 100 or metrics.overdue_payables > 1000,
            "concentrationRelevant": metrics.receivable_top_share >= 60 or metrics.expense_concentration_top_share >= 35,
            "delaysDetected": metrics.overdue_receivables > 0 or metrics.overdue_payables > 0,
            "snapshotFirst": True,
        }


_commitments: FinancialCommitmentsIntelligence | None = None


def get_financial_commitments_intelligence() -> FinancialCommitmentsIntelligence:
    global _commitments
    if _commitments is None:
        _commitments = FinancialCommitmentsIntelligence()
    return _commitments
