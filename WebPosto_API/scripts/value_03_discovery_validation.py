#!/usr/bin/env python3
"""VALUE-03 — validação runtime do Discovery Engine com ExpenseDetector."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "validation" / "VALUE_03_DISCOVERY_RAW.json"


def _candidate_row(candidate, *, priority: float | None, final_state: str, reason: str = "") -> dict:
    money = candidate.money_found
    return {
        "tenant": candidate.tenant,
        "tenant_name": candidate.tenant_name,
        "detector": candidate.detector_name,
        "candidate_type": (candidate.evidence or {}).get("anomaly_type") or candidate.category.value,
        "title": candidate.title,
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
    from src.services.decision_discovery.detectors import ExpenseDetector, FuelRevenueDetector
    from src.services.decision_discovery.models import DecisionCandidate
    from src.services.decision_discovery.root_cause.investigators import ExpenseRootCause
    from src.services.decision_discovery.root_cause.root_cause_engine import RootCauseEngine
    from src.services.decision_discovery.models import DecisionCategory
    from src.services.performance.performance_metrics import performance_metrics
    from src.services.tenant_discovery_service import TenantDiscoveryService

    end = date.today()
    data_final = end.isoformat()
    data_inicial = (end - timedelta(days=7)).isoformat()

    discovery = await TenantDiscoveryService().discover_tenants()
    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())
    engine.register_detector(ExpenseDetector())

    performance_metrics.reset()
    t0 = time.perf_counter()
    result = await engine.discover_all_tenants(
        tenants=discovery.tenants_discovered,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=5,
        analysis_id="value-03-validation",
    )
    cold_ms = round((time.perf_counter() - t0) * 1000, 1)

    t1 = time.perf_counter()
    result_warm = await engine.discover_all_tenants(
        tenants=discovery.tenants_discovered,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=5,
        analysis_id="value-03-validation-warm",
    )
    warm_ms = round((time.perf_counter() - t1) * 1000, 1)

    all_before: list[dict] = []
    approved_ids = {c.id for c in result.all_candidates}
    rejected_map = {str((r.get("candidate") or {}).get("id")): r for r in result.rejected_candidates}

    for candidate in result.all_candidates + [
        (item.get("candidate") or {}) for item in result.rejected_candidates if item.get("candidate")
    ]:
        if isinstance(candidate, dict):
            continue
        if candidate.id in approved_ids:
            all_before.append(
                _candidate_row(candidate, priority=candidate.priority_value, final_state="DECISION")
            )
        else:
            rej = rejected_map.get(candidate.id, {})
            state = "OBSERVATION" if rej.get("observation_reason") else "DISCARDED"
            all_before.append(
                _candidate_row(
                    candidate,
                    priority=rej.get("priority_score"),
                    final_state=state,
                    reason=rej.get("discard_reason") or rej.get("observation_reason") or rej.get("reason") or "",
                )
            )

    for item in result.rejected_candidates:
        cand_dict = item.get("candidate") or {}
        cid = str(cand_dict.get("id") or "")
        if any(r.get("tenant") == cand_dict.get("tenant") and r.get("detector") == cand_dict.get("detector") for r in all_before):
            continue
        conf = item.get("confidence", cand_dict.get("confidence"))
        money = cand_dict.get("money_found") or {}
        impact = money.get("total") or money.get("at_risk") or item.get("money_found")
        all_before.append(
            {
                "tenant": cand_dict.get("tenant"),
                "tenant_name": cand_dict.get("tenant_name"),
                "detector": item.get("detector") or cand_dict.get("detector"),
                "candidate_type": (cand_dict.get("evidence") or {}).get("anomaly_type"),
                "title": item.get("title") or cand_dict.get("title"),
                "impact": impact,
                "confidence": conf,
                "priority_score": item.get("priority_score"),
                "final_state": "OBSERVATION" if item.get("observation_reason") else "DISCARDED",
                "reason": item.get("discard_reason") or item.get("observation_reason") or item.get("reason"),
            }
        )

    top = result.all_candidates[0] if result.all_candidates else None
    root_cause = None
    if top and top.detector_name == "ExpenseDetector":
        rc_engine = RootCauseEngine()
        rc_engine.register_investigator(DecisionCategory.COST, ExpenseRootCause())
        rc = await rc_engine.investigate(top)
        if rc.success and rc.analysis:
            root_cause = rc.analysis.to_dict()

    report = {
        "executed_at": data_final,
        "period": {"start": data_inicial, "end": data_final},
        "tenants_discovered": [t.tenant_id for t in discovery.tenants_discovered],
        "detectors": ["FuelRevenueDetector", "ExpenseDetector"],
        "candidates_before_ranking": all_before,
        "approved_decisions": [_candidate_row(c, priority=c.priority_value, final_state="DECISION") for c in result.all_candidates],
        "global_winner": _candidate_row(top, priority=top.priority_value, final_state="DECISION") if top else None,
        "performance": {
            "full_analysis_cold_ms": cold_ms,
            "full_analysis_warm_ms": warm_ms,
            "expense_cache_hits": performance_metrics.expense_cache_hit_count,
            "expense_cache_misses": performance_metrics.expense_cache_miss_count,
            "fuel_cache_hits": performance_metrics.fuel_cache_hit_count,
            "fuel_cache_misses": performance_metrics.fuel_cache_miss_count,
        },
        "root_cause_top_expense": root_cause,
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
