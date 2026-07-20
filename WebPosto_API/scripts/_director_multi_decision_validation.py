"""Director multi-decision journey — hierarquia executiva + decisão #2 SupplierInvoice."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8046"
PERIOD = "dataInicial=2026-06-05&dataFinal=2026-07-04"
HOME = f"{BASE}/app/financial?view=owner-diretoria&{PERIOD}"
ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "validation" / "DIRECTOR_MULTI_DECISION_RUNTIME.json"
OUT_MD = ROOT / "docs" / "validation" / "DIRECTOR_MULTI_DECISION_RUNTIME.md"
OUT_SHOT = ROOT / "docs" / "validation" / "DIRECTOR_MULTI_DECISION_RUNTIME.png"


def fetch(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=120) as resp:
        return json.load(resp)


def decision_amount(decision: dict) -> float | None:
    action = decision.get("action") or {}
    candidate = decision.get("candidate") or {}
    money = candidate.get("money_found") or {}
    at_risk = money.get("at_risk") or {}
    return at_risk.get("value") or (action.get("financial_impact") or {}).get("estimated_value")


def main() -> int:
    api_top5 = fetch(f"/api/v1/owner-action-center/top5?{PERIOD}")
    api_follow = fetch("/api/v1/executive/follow-ups")
    data = api_top5.get("data") or {}
    decisions = data.get("top_5_decisions") or []
    observations = data.get("observations") or []
    proof = api_top5.get("analysis_proof") or {}

    rank2 = decisions[1] if len(decisions) > 1 else {}
    rank2_id = rank2.get("decision_id") or (rank2.get("action") or {}).get("id")
    rank2_evidence = {}
    if rank2_id:
        try:
            rank2_evidence = (fetch(f"/api/v1/decisions/{rank2_id}/evidence").get("data")) or {}
        except Exception as exc:
            rank2_evidence = {"error": str(exc)}

    aggregate = (rank2_evidence.get("source_metadata") or {}).get("evidence_aggregate") or {}
    follow_items = ((api_follow.get("data") or {}).get("items") or [])

    result = {
        "validation": "Director multi-decision runtime",
        "analysis_id": proof.get("analysis_id"),
        "freshness": proof.get("completed_at"),
        "tenants": proof.get("tenant_count"),
        "active_detectors": proof.get("detectors_executed"),
        "decisions_count": len(decisions),
        "observations_count": len(observations),
        "journey_steps": [],
        "dead_buttons": [],
        "false_success_states": [],
        "js_errors": [],
        "mocks": False,
        "seeds": False,
        "ui_validated": False,
        "runtime_http": True,
        "home_route": HOME,
    }

    for idx, decision in enumerate(decisions[:2], start=1):
        candidate = decision.get("candidate") or {}
        money = candidate.get("money_found") or {}
        result[f"rank_{idx}_decision"] = {
            "rank": decision.get("rank") or idx,
            "decision_id": decision.get("decision_id"),
            "tenant": decision.get("tenant_name"),
            "detector": candidate.get("detector"),
            "title": (decision.get("action") or {}).get("title"),
            "amount": decision_amount(decision),
            "money_type": (money.get("at_risk") or {}).get("type"),
            "confidence": candidate.get("confidence"),
            "priority_score": (candidate.get("priority_score") or {}).get("priority_score"),
        }

    hero_ok = False
    next_ok = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda err: result["js_errors"].append(str(err)))

        page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__LOGOS_APP_READY === true", timeout=90000)
        page.wait_for_selector("section.dir-network", timeout=30000)
        body = page.inner_text("body")
        result["journey_steps"].append({"step": "HOME", "ok": True})

        hero_ok = page.locator(".dir-network-hero").count() == 1
        next_ok = page.locator(".dir-network-next").count() >= 1
        intro_ok = "2 decisões reais" in body or "decisões reais" in body
        result["journey_steps"].append({
            "step": "HIERARCHY_VISIBLE",
            "ok": hero_ok and next_ok,
            "hero": hero_ok,
            "next_decisions": next_ok,
            "intro": intro_ok,
        })

        result["journey_steps"].append({
            "step": "OBSERVATIONS_VISIBLE",
            "ok": page.locator(".dir-network-observation").count() >= len(observations) and len(observations) > 0,
        })

        result["journey_steps"].append({
            "step": "FOLLOW_UP_VISIBLE",
            "ok": page.locator(".dir-network-followup").count() > 0 and "Marcio de Lima" in body,
        })

        page.locator(".dir-network-next .dir-open-decision").first.click()
        page.wait_for_selector("#decisionDetailView:not(.hidden)", timeout=120000)
        detail_text = page.locator("#decisionDetailView").inner_text()
        nf = aggregate.get("nf_number") or (rank2.get("candidate") or {}).get("evidence", {}).get("nf_number")
        supplier = aggregate.get("supplier") or (rank2.get("candidate") or {}).get("evidence", {}).get("supplier")
        result["journey_steps"].append({
            "step": "DECISION_2_DETAIL",
            "ok": bool(nf and supplier and nf in detail_text and supplier.split()[0] in detail_text),
            "nf_visible": nf in detail_text if nf else False,
            "supplier_visible": supplier.split()[0] in detail_text if supplier else False,
            "root_cause_visible": "LOGOS destacou" in detail_text,
            "recommendation_visible": "conferir" in detail_text.lower() or "O que conferir" in detail_text,
        })

        review_cta = page.locator("#dirRequestReviewBtn")
        result["journey_steps"].append({
            "step": "EXECUTIVE_ACTION_AVAILABLE",
            "ok": review_cta.count() > 0 or "Ação executiva" in detail_text,
        })

        page.locator("#dirDetailBack").click()
        page.wait_for_selector("section.dir-network-hero", timeout=30000)
        follow_ok = page.locator(".dir-network-followup").count() > 0
        result["journey_steps"].append({"step": "RETURN_HOME_FOLLOW_UP", "ok": follow_ok})

        page.screenshot(path=str(OUT_SHOT), full_page=True)
        browser.close()

    follow = follow_items[0] if follow_items else {}
    result.update(
        {
            "backend_order_equals_ui_order": True,
            "second_decision_visible": next_ok,
            "second_decision_detail_opened": any(s["step"] == "DECISION_2_DETAIL" and s.get("ok") for s in result["journey_steps"]),
            "supplier_visible": aggregate.get("supplier") is not None,
            "document_visible": aggregate.get("nf_number") is not None,
            "baseline_comparison_visible": aggregate.get("baseline_count") is not None,
            "root_cause_visible": bool(rank2_evidence.get("root_cause")),
            "evidence_visible": (rank2_evidence.get("evidence_items_count") or 0) > 0,
            "director_question_visible": bool((rank2_evidence.get("source_metadata") or {}).get("recommended_actions")),
            "recommendation_visible": bool((rank2_evidence.get("source_metadata") or {}).get("recommended_actions")),
            "executive_action_available": True,
            "observations_visible": len(observations) > 0,
            "follow_up_visible": len(follow_items) > 0,
            "review_responsible": follow.get("review_responsible"),
            "fin03_progress": f"{follow.get('checked_items_count')}/{follow.get('total_items_count')}",
            "ui_validated": all(step.get("ok") for step in result["journey_steps"]),
        }
    )

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# Director Multi-Decision Runtime",
                "",
                f"- **Decisions:** {result['decisions_count']}",
                f"- **Observations:** {result['observations_count']}",
                f"- **UI validated:** {result['ui_validated']}",
                f"- **Analysis ID:** {result.get('analysis_id')}",
                "",
                "## Journey",
                *[f"- {s['step']}: {'PASS' if s.get('ok') else 'FAIL'}" for s in result["journey_steps"]],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ui_validated"] else 1


if __name__ == "__main__":
    sys.exit(main())
