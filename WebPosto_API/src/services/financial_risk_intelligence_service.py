"""F08.4 IA-2 — Financial Risk Engine (evidência + lineage)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.services.financial_intelligence_evidence import (
    PeriodEvidence,
    build_lineage,
    delta_pct,
    get_financial_intelligence_evidence,
)
from src.services.financial_snapshot_config import get_financial_snapshot_config

RISK_LEVELS = ("BAIXO", "MODERADO", "ALTO", "CRÍTICO")


def _level_from_score(score: int) -> str:
    if score >= 75:
        return "CRÍTICO"
    if score >= 50:
        return "ALTO"
    if score >= 25:
        return "MODERADO"
    return "BAIXO"


class FinancialRiskIntelligenceService:
    def __init__(self) -> None:
        self._evidence = get_financial_intelligence_evidence()

    def _resolve_period(
        self,
        data_inicial: str | None,
        data_final: str | None,
    ) -> tuple[str, str]:
        cfg = get_financial_snapshot_config()
        return data_inicial or cfg.default_period()[0], data_final or cfg.default_period()[1]

    def detect(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        start, end = self._resolve_period(data_inicial, data_final)
        current = self._evidence.load_period(start, end, empresa_codigo)
        periods = self._evidence.discover_periods(empresa_codigo)
        metrics = self._evidence.compute_metrics(current)
        baseline_meta = periods[1] if len(periods) > 1 else None
        baseline = (
            self._evidence.load_period(baseline_meta["dataInicial"], baseline_meta["dataFinal"], empresa_codigo)
            if baseline_meta
            else None
        )
        comparison = self._evidence.compare_periods(current, baseline)
        deltas = comparison.get("deltas") or {}

        risks: list[dict[str, Any]] = []

        despesas_delta = deltas.get("despesas")
        receitas_delta = deltas.get("receitas")
        if despesas_delta is not None and receitas_delta is not None and despesas_delta > receitas_delta + 5:
            severity = min(100, int((despesas_delta - receitas_delta) * 2))
            risks.append(
                {
                    "code": "EXPENSE_OUTPACING_REVENUE",
                    "title": "Despesas crescendo acima da receita",
                    "level": _level_from_score(severity),
                    "evidence": {
                        "despesasDeltaPct": despesas_delta,
                        "receitasDeltaPct": receitas_delta,
                    },
                    "lineage": {
                        "current": build_lineage("financial_overview", current.overview, metric="despesas"),
                        "baseline": build_lineage("financial_overview", baseline.overview if baseline else None, metric="receitas"),
                        "lineage": True,
                    },
                }
            )

        if metrics.expense_concentration_top_share >= 35:
            severity = min(100, int(metrics.expense_concentration_top_share))
            risks.append(
                {
                    "code": "EXPENSE_CONCENTRATION",
                    "title": "Concentração excessiva de despesas",
                    "level": _level_from_score(severity),
                    "evidence": {"topCategorySharePct": metrics.expense_concentration_top_share},
                    "lineage": {
                        "current": build_lineage("financial_expenses", current.expenses, metric="concentration"),
                        "lineage": True,
                    },
                }
            )

        if metrics.receivable_top_share >= 60 and metrics.recebimentos > 0:
            severity = min(100, int(metrics.receivable_top_share))
            risks.append(
                {
                    "code": "RECEIVABLE_DEPENDENCY",
                    "title": "Dependência de poucos recebíveis",
                    "level": _level_from_score(severity),
                    "evidence": {"topReceivableSharePct": metrics.receivable_top_share},
                    "lineage": {
                        "current": build_lineage("financial_receivables", current.receivables, metric="concentration"),
                        "lineage": True,
                    },
                }
            )

        fluxo_delta = deltas.get("fluxo")
        if fluxo_delta is not None and fluxo_delta < -5:
            severity = min(100, int(abs(fluxo_delta) * 2))
            risks.append(
                {
                    "code": "CASH_FLOW_DETERIORATION",
                    "title": "Fluxo de caixa deteriorando",
                    "level": _level_from_score(severity),
                    "evidence": {"fluxoDeltaPct": fluxo_delta, "currentFluxo": float(metrics.fluxo)},
                    "lineage": {
                        "current": build_lineage("financial_overview", current.overview, metric="fluxo"),
                        "baseline": build_lineage("financial_overview", baseline.overview if baseline else None, metric="fluxo"),
                        "lineage": True,
                    },
                }
            )

        if metrics.fluxo < 0:
            risks.append(
                {
                    "code": "NEGATIVE_CASH_FLOW",
                    "title": "Fluxo negativo no período",
                    "level": "ALTO" if metrics.fluxo > -50000 else "CRÍTICO",
                    "evidence": {"fluxo": float(metrics.fluxo)},
                    "lineage": {
                        "current": build_lineage("financial_overview", current.overview, metric="fluxo"),
                        "lineage": True,
                    },
                }
            )

        if not risks:
            risks.append(
                {
                    "code": "NO_MATERIAL_RISK",
                    "title": "Sem risco material detectado no snapshot",
                    "level": "BAIXO",
                    "evidence": {"snapshotsAvailable": len(periods)},
                    "lineage": build_lineage("financial_overview", current.overview, metric="risk_scan"),
                }
            )

        level_rank = {"BAIXO": 0, "MODERADO": 1, "ALTO": 2, "CRÍTICO": 3}
        overall = max(risks, key=lambda r: level_rank.get(str(r.get("level")), 0))

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": start, "dataFinal": end},
            "empresaCodigo": empresa_codigo,
            "overallLevel": overall["level"],
            "risks": risks,
            "riskCount": len([r for r in risks if r["code"] != "NO_MATERIAL_RISK"]),
            "snapshotFirst": True,
        }


_risk: FinancialRiskIntelligenceService | None = None


def get_financial_risk_intelligence() -> FinancialRiskIntelligenceService:
    global _risk
    if _risk is None:
        _risk = FinancialRiskIntelligenceService()
    return _risk
