"""F08.4 IA-4 — Cash Flow Intelligence (histórico, sem forecast)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.services.financial_intelligence_evidence import (
    build_lineage,
    classify_trend,
    get_financial_intelligence_evidence,
)
from src.services.financial_snapshot_config import get_financial_snapshot_config


class CashFlowIntelligenceService:
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
        periods = self._evidence.discover_periods(empresa_codigo)
        metrics = self._evidence.compute_metrics(current)

        history: list[dict[str, Any]] = []
        for meta in periods[:6]:
            ev = self._evidence.load_period(meta["dataInicial"], meta["dataFinal"], empresa_codigo)
            m = self._evidence.compute_metrics(ev)
            history.append(
                {
                    "period": {"dataInicial": meta["dataInicial"], "dataFinal": meta["dataFinal"]},
                    "fluxo": float(m.fluxo),
                    "recebimentos": float(m.recebimentos),
                    "despesas": float(m.despesas),
                    "lineage": build_lineage("financial_overview", ev.overview, metric="fluxo"),
                }
            )

        baseline_meta = periods[1] if len(periods) > 1 else None
        baseline = (
            self._evidence.load_period(baseline_meta["dataInicial"], baseline_meta["dataFinal"], empresa_codigo)
            if baseline_meta
            else None
        )
        comparison = self._evidence.compare_periods(current, baseline)
        fluxo_delta = (comparison.get("deltas") or {}).get("fluxo")

        healthy = metrics.fluxo >= 0
        deteriorating = fluxo_delta is not None and fluxo_delta < -5
        trend = classify_trend(fluxo_delta)

        strongest = max(history, key=lambda h: h["fluxo"], default=None)
        weakest = min(history, key=lambda h: h["fluxo"], default=None)

        health_label = "SAUDÁVEL" if healthy and not deteriorating else "ATENÇÃO" if healthy else "DETERIORADO"

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": start, "dataFinal": end},
            "empresaCodigo": empresa_codigo,
            "fluxoSaudavel": healthy,
            "fluxoDeteriorando": deteriorating,
            "cashFlowHealth": health_label,
            "trend": trend,
            "currentFluxo": float(metrics.fluxo),
            "fluxoDeltaPct": fluxo_delta,
            "strongestPeriod": strongest,
            "weakestPeriod": weakest,
            "history": history,
            "snapshotFirst": True,
            "forecast": None,
            "lineage": build_lineage("financial_overview", current.overview, metric="cash_flow"),
        }


_cash_flow: CashFlowIntelligenceService | None = None


def get_cash_flow_intelligence() -> CashFlowIntelligenceService:
    global _cash_flow
    if _cash_flow is None:
        _cash_flow = CashFlowIntelligenceService()
    return _cash_flow
