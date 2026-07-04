#!/usr/bin/env python3
"""VALUE-04 — validação runtime Discovery com 3 detectores."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "validation" / "VALUE_04_DISCOVERY_RAW.json"


def _row(candidate, *, priority, final_state, reason="") -> dict:
    money = candidate.money_found
    ev = candidate.evidence or {}
    return {
        "tenant": candidate.tenant,
        "tenant_name": candidate.tenant_name,
        "detector": candidate.detector_name,
        "signal_type": ev.get("signal_type") or ev.get("anomaly_type"),
        "impact": round(money.total_impact(), 2),
        "at_risk": round(money.at_risk, 2),
        "at_risk_type": money.at_risk_type.value,
        "confidence": round(candidate.confidence, 4),
        "priority_score": priority,
        "final_state": final_state,
        "reason": reason,
    }


async def main() -> None:
    from src.services.decision_discovery import DecisionDiscoveryEngine
    from src.services.decision_discovery.detectors import (
        CardReceivableDetector,
        ExpenseDetector,
        FuelRevenueDetector,
    )
    from src.services.decision_discovery.models import DecisionCandidate
    from src.services.performance.performance_metrics import performance_metrics
    from src.services.tenant_discovery_service import TenantDiscoveryService

    end = date.today()
    data_final = end.isoformat()
    data_inicial = (end - timedelta(days=7)).isoformat()

    discovery = await TenantDiscoveryService().discover_tenants()
    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())
    engine.register_detector(ExpenseDetector())
    engine.register_detector(CardReceivableDetector())

    performance_metrics.reset()
    wp_before = performance_metrics.webposto_request_total

    t0 = time.perf_counter()
    result = await engine.discover_all_tenants(
        tenants=discovery.tenants_discovered,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=5,
        analysis_id="value-04-validation-cold",
    )
    cold_ms = round((time.perf_counter() - t0) * 1000, 1)
    wp_cold = performance_metrics.webposto_request_total - wp_before

    t1 = time.perf_counter()
    result_warm = await engine.discover_all_tenants(
        tenants=discovery.tenants_discovered,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=5,
        analysis_id="value-04-validation-warm",
    )
    warm_ms = round((time.perf_counter() - t1) * 1000, 1)
    wp_warm = performance_metrics.webposto_request_total - wp_before - wp_cold

    all_rows = []
    approved_ids = {c.id for c in result.all_candidates}
    for c in result.all_candidates:
        all_rows.append(_row(c, priority=c.priority_value, final_state="DECISION"))
    for item in result.rejected_candidates:
        cand = item.get("candidate") or {}
        if not cand:
            continue
        state = "OBSERVATION" if item.get("observation_reason") else "DISCARDED"
        from src.services.decision_discovery.models import MoneyFound

        class _C:
            pass

        o = _C()
        o.tenant = cand.get("tenant")
        o.tenant_name = cand.get("tenant_name")
        o.detector_name = item.get("detector") or cand.get("detector")
        o.evidence = cand.get("evidence") or {}
        mf = cand.get("money_found") or {}
        o.money_found = MoneyFound(
            at_risk=float(mf.get("at_risk", {}).get("value", mf.get("at_risk", 0)) if isinstance(mf.get("at_risk"), dict) else mf.get("at_risk", 0)),
            recoverable=float(mf.get("recoverable", {}).get("value", mf.get("recoverable", 0)) if isinstance(mf.get("recoverable"), dict) else mf.get("recoverable", 0)),
        )
        o.confidence = item.get("confidence", cand.get("confidence", 0))
        if cand.get("id") not in approved_ids:
            all_rows.append(
                _row(o, priority=item.get("priority_score"), final_state=state, reason=item.get("discard_reason") or item.get("observation_reason") or "")
            )

    by_detector = {}
    for d in ("FuelRevenueDetector", "ExpenseDetector", "CardReceivableDetector"):
        by_detector[d] = sum(1 for r in all_rows if r["detector"] == d)

    top = result.all_candidates[0] if result.all_candidates else None
    report = {
        "executed_at": data_final,
        "period": {"start": data_inicial, "end": data_final},
        "candidates_before_ranking": all_rows,
        "counts_by_detector": by_detector,
        "approved_decisions": [_row(c, priority=c.priority_value, final_state="DECISION") for c in result.all_candidates],
        "global_winner": _row(top, priority=top.priority_value, final_state="DECISION") if top else None,
        "performance": {
            "full_analysis_cold_ms": cold_ms,
            "full_analysis_warm_ms": warm_ms,
            "receivable_cache_hits": performance_metrics.receivable_cache_hit_count,
            "receivable_cache_misses": performance_metrics.receivable_cache_miss_count,
            "expense_cache_hits": performance_metrics.expense_cache_hit_count,
            "expense_cache_misses": performance_metrics.expense_cache_miss_count,
            "fuel_cache_hits": performance_metrics.fuel_cache_hit_count,
            "fuel_cache_misses": performance_metrics.fuel_cache_miss_count,
            "webposto_requests_cold": wp_cold,
            "webposto_requests_warm": wp_warm,
        },
        "thresholds": {
            "min_decision_confidence": DecisionCandidate.MIN_DECISION_CONFIDENCE,
            "min_decision_impact_brl": DecisionCandidate.MIN_DECISION_IMPACT_BRL,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "decisions": len(result.all_candidates), "cold_ms": cold_ms}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
