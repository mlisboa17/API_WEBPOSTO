"""F08.4 IA-1 — Financial Trend Engine (snapshot-first, sem previsão)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.services.financial_intelligence_evidence import (
    HORIZONS,
    PeriodEvidence,
    build_lineage,
    classify_trend,
    delta_pct,
    get_financial_intelligence_evidence,
)
from src.services.financial_snapshot_config import get_financial_snapshot_config

DIMENSIONS = ("receitas", "despesas", "fluxo", "recebimentos", "pagamentos")
METRIC_ATTR = {
    "receitas": "receitas",
    "despesas": "despesas",
    "fluxo": "fluxo",
    "recebimentos": "recebimentos",
    "pagamentos": "pagamentos",
}


class FinancialTrendIntelligenceService:
    def __init__(self) -> None:
        self._evidence = get_financial_intelligence_evidence()

    def _resolve_period(
        self,
        data_inicial: str | None,
        data_final: str | None,
    ) -> tuple[str, str]:
        cfg = get_financial_snapshot_config()
        return data_inicial or cfg.default_period()[0], data_final or cfg.default_period()[1]

    def _baseline_evidence(self, meta: dict[str, Any] | None, empresa_codigo: str | int | None) -> PeriodEvidence | None:
        if not meta:
            return None
        return self._evidence.load_period(meta["dataInicial"], meta["dataFinal"], empresa_codigo)

    def analyze(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        start, end = self._resolve_period(data_inicial, data_final)
        current = self._evidence.load_period(start, end, empresa_codigo)
        periods = self._evidence.discover_periods(empresa_codigo)
        current_metrics = self._evidence.compute_metrics(current)

        horizons: dict[str, Any] = {}
        for horizon in HORIZONS:
            baseline_meta = self._evidence.pick_baseline_period(periods, current, horizon)
            baseline = self._baseline_evidence(baseline_meta, empresa_codigo)
            dimension_rows: dict[str, Any] = {}
            for dim in DIMENSIONS:
                attr = METRIC_ATTR[dim]
                current_val = getattr(current_metrics, attr)
                if not baseline:
                    dimension_rows[dim] = {
                        "classification": "INDETERMINADO",
                        "deltaPct": None,
                        "currentValue": float(current_val),
                        "evidenceAvailable": False,
                        "lineage": build_lineage(
                            f"financial_{'overview' if dim in {'despesas', 'pagamentos'} else 'receivables'}",
                            current.overview if dim in {"despesas", "pagamentos"} else current.receivables,
                            metric=dim,
                        ),
                    }
                    continue
                prev_metrics = self._evidence.compute_metrics(baseline)
                prev_val = getattr(prev_metrics, attr)
                change = delta_pct(current_val, prev_val)
                dimension_rows[dim] = {
                    "classification": classify_trend(change),
                    "deltaPct": change,
                    "currentValue": float(current_val),
                    "previousValue": float(prev_val),
                    "evidenceAvailable": True,
                    "baselinePeriod": baseline_meta,
                    "lineage": {
                        "current": build_lineage(
                            "financial_overview" if dim in {"despesas", "pagamentos", "fluxo"} else "financial_receivables",
                            current.overview if dim != "recebimentos" else current.receivables,
                            metric=dim,
                        ),
                        "baseline": build_lineage(
                            "financial_overview",
                            baseline.overview,
                            metric=dim,
                        ),
                        "lineage": True,
                    },
                }
            horizons[horizon] = dimension_rows

        overall_counts = {"CRESCIMENTO": 0, "ESTABILIDADE": 0, "QUEDA": 0, "INDETERMINADO": 0}
        for horizon_data in horizons.values():
            for row in horizon_data.values():
                overall_counts[row["classification"]] = overall_counts.get(row["classification"], 0) + 1
        overall = max(
            ("CRESCIMENTO", "ESTABILIDADE", "QUEDA"),
            key=lambda k: overall_counts.get(k, 0),
        )

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": start, "dataFinal": end},
            "empresaCodigo": empresa_codigo,
            "horizons": horizons,
            "overallTrend": overall,
            "snapshotsAvailable": len(periods),
            "snapshotFirst": True,
        }


_trend: FinancialTrendIntelligenceService | None = None


def get_financial_trend_intelligence() -> FinancialTrendIntelligenceService:
    global _trend
    if _trend is None:
        _trend = FinancialTrendIntelligenceService()
    return _trend
